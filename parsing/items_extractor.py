"""Extract receipt items — and the discounts attached to them — from HTML."""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from .discount_extractor import parse_discount_group
from .money import to_float, to_str

# A bare price on its own span, e.g. "12,77" (German layout puts the line
# total in a dedicated css_bold span).
_BARE_PRICE_RE = re.compile(r"^\d+[,.]\d{2}$")
# A "quantity x unit price" calculation line, e.g. "4,000 x 1,32".  These are
# never line totals.
_CALC_LINE_RE = re.compile(r"\d+[,.]\d+\s*[xX]\s*\d")
# A line total at the end of the description line, optionally followed by the
# single-letter tax type, e.g. "БИСКВИТИ КАКАО    5,28 B".
_TRAILING_TOTAL_RE = re.compile(r"(\d+[,.]\d{2})\s*[A-ZА-Я]?\s*$")


def _span_classes(span: Tag) -> List[str]:
    classes = span.get("class") or []
    if isinstance(classes, str):
        return [classes]
    return list(classes)


def _extract_line_total(spans: List[Tag]) -> Optional[str]:
    """Find the printed total for an article, as it appears on the receipt.

    The printed amount must be preferred over ``quantity * unit_price``:
    weighed items are rounded per line by the till, so e.g. 2,398 kg at 0,99
    prints as 2,37 while the multiplication gives 2,374.  Summing recomputed
    values drifts away from the receipt total by a cent or more.
    """
    # German layout: the total sits alone in a bold span.
    for span in spans:
        if "css_bold" in _span_classes(span):
            text = span.get_text().strip()
            if _BARE_PRICE_RE.match(text):
                return text.replace(".", ",")

    # Bulgarian layout: the total trails the description text.
    for span in spans:
        text = span.get_text().strip()
        if _CALC_LINE_RE.search(text):
            continue
        match = _TRAILING_TOTAL_RE.search(text)
        if match:
            return match.group(1).replace(".", ",")

    return None


def _extract_precise_quantity(spans: List[Tag], art_quantity: str) -> str:
    """Recover full weight precision for kg items from the visible text.

    The data-art-quantity attribute is truncated to 1 decimal by Lidl's
    server, while the visible receipt text has full precision.  Two known
    formats: "0,248 kg" / "0,248 кг" and "0,248 x 3,55" (Lidl Bulgaria).
    """
    api_decimal = re.search(r"[,\.](\d+)", art_quantity)
    if api_decimal and len(api_decimal.group(1)) >= 3:
        return art_quantity  # API already precise

    for span in spans:
        span_text = span.get_text()
        weight_match = re.search(
            r"(\d+[,\.]\d{2,})\s*(?:kg|кг|КГ)", span_text
        ) or re.search(r"(\d+[,\.]\d{2,})\s*x\s*\d", span_text)
        if not weight_match:
            continue

        text_qty_str = weight_match.group(1)
        text_val = to_float(text_qty_str)
        api_val = to_float(art_quantity)
        if text_val is None:
            return text_qty_str
        if api_val is not None and abs(text_val - api_val) >= 0.1:
            print(
                f"Warnung: Sichtbarer Text-Gewichtswert '{text_qty_str}' "
                f"weicht erheblich vom API-Wert '{art_quantity}' ab "
                f"— API-Wert wird verwendet"
            )
            return art_quantity
        return text_qty_str

    return art_quantity


def _determine_unit(spans: List[Tag], art_quantity: str) -> str:
    """Decide whether an item is sold by weight or by the piece.

    Primary signal: a non-integer quantity (e.g. "0,7") means priced per kg.
    Whole-number quantities with a trailing ",0" (e.g. "2,0" for 2 pieces)
    must remain stk.
    """
    qty_float = to_float(art_quantity)
    if qty_float is not None and qty_float != int(qty_float):
        return "kg"

    for span in spans:
        span_text = span.get_text()
        if "kg" in span_text or "кг" in span_text or "КГ" in span_text:
            return "kg"

    return "stk"


def extract_receipt_items_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract items with their per-line discounts.

    Discounts are printed immediately after the article they reduce, so the
    spans are walked in document order and each discount group is attributed
    to the most recent article.
    """
    items: List[Dict[str, Any]] = []
    try:
        relevant_spans = [
            span
            for span in soup.find_all("span")
            if {"article", "discount"} & set(_span_classes(span))
        ]

        if not any("article" in _span_classes(s) for s in relevant_spans):
            print("Keine Artikel-Spans gefunden")
            return items

        # Each printed receipt line is one item.  A line's spans are
        # contiguous, so a *block* of consecutive spans sharing the same
        # article id and description is grouped together — but the same
        # article appearing again further down the receipt (a second bottle,
        # a second weighing of loose fruit) starts a new block and stays a
        # separate item.  Grouping by article id alone would silently merge
        # those and drop a line's worth of money from the total.
        items_by_key: Dict[str, List[Tag]] = {}
        discounts_by_key: Dict[str, List[Dict[str, Any]]] = {}
        key_order: List[str] = []

        current_key: Optional[str] = None
        previous_article_key: Optional[str] = None
        block_index = 0
        pending_discount: List[Tag] = []
        pending_promotion: Optional[str] = None

        def flush_discount() -> None:
            """Finish the discount group being accumulated, if any."""
            nonlocal pending_discount, pending_promotion
            if pending_discount and current_key is not None:
                discount = parse_discount_group(pending_discount)
                if discount:
                    discounts_by_key.setdefault(current_key, []).append(discount)
            pending_discount = []
            pending_promotion = None

        for span in relevant_spans:
            classes = _span_classes(span)

            if "discount" in classes:
                promotion_id = span.get("data-promotion-id") or ""
                # A new promotion id starts a new discount group.
                if pending_discount and promotion_id != pending_promotion:
                    flush_discount()
                pending_promotion = promotion_id
                pending_discount.append(span)
                continue

            # An article span ends any discount group being accumulated.
            flush_discount()

            art_id = span.get("data-art-id")
            art_description = span.get("data-art-description", "")
            if not art_id or not art_description:
                continue

            article_key = f"{art_id}_{art_description}"
            if article_key != previous_article_key:
                block_index += 1
                previous_article_key = article_key

            key = f"{block_index}_{article_key}"
            if key not in items_by_key:
                items_by_key[key] = []
                key_order.append(key)
            items_by_key[key].append(span)
            current_key = key

        flush_discount()

        for key in key_order:
            spans = items_by_key[key]
            try:
                main_span = spans[0]

                art_description = main_span.get("data-art-description", "")
                art_quantity = main_span.get("data-art-quantity", "1")
                unit_price = main_span.get("data-unit-price", "")

                if not art_description or not unit_price:
                    continue

                unit = _determine_unit(spans, art_quantity)
                if unit == "kg":
                    art_quantity = _extract_precise_quantity(spans, art_quantity)

                line_total = _extract_line_total(spans)
                if line_total is None:
                    # Fall back to recomputing from quantity and unit price.
                    qty = to_float(art_quantity, 1.0)
                    price = to_float(unit_price, 0.0)
                    line_total = to_str(round(qty * price, 2))

                discounts = discounts_by_key.get(key, [])
                discount_sum = sum(
                    to_float(d["amount"], 0.0) or 0.0 for d in discounts
                )

                gross = to_float(line_total, 0.0) or 0.0
                item: Dict[str, Any] = {
                    "art_id": main_span.get("data-art-id"),
                    "name": art_description,
                    "price": unit_price,
                    "quantity": art_quantity,
                    "unit": unit,
                    "line_total": line_total,
                    "discounts": discounts,
                    "discount_total": to_str(discount_sum) if discounts else None,
                    "net_total": to_str(round(gross - discount_sum, 2)),
                }

                tax_type = main_span.get("data-tax-type")
                if tax_type:
                    item["tax_type"] = tax_type

                items.append(item)

            except Exception as e:
                print(f"Fehler beim Extrahieren eines Artikels: {e}")

    except Exception as e:
        print(f"Artikel nicht gefunden: {e}")

    return items
