"""Main receipt HTML parser.

A note on ``total_price`` (IMPORTANT — a downstream ledger reads this field):

``total_price`` is the amount actually **charged**, i.e. net of all discounts.
That has always been its documented meaning, but until per-line discounts were
parsed it silently equalled the gross total on every non-German receipt,
because the discount detection was German-text-based ("Preisvorteil",
"Rabatt", "zu zahlen") and matched nothing on e.g. Bulgarian receipts.  Every
couponed trip was therefore overstated.

The fields now are:

``total_price``           what the card was charged  (gross - discounts)
``total_price_gross``     sum of the printed line totals, before discounts
``total_price_no_saving`` unchanged alias of ``total_price_gross`` (compat)
``discount_total``        every discount on the receipt
``lidlplus_saved_amount`` the Lidl Plus coupon share of that
``sticker_discount_amount`` the in-store markdown share of that
``total_price_source``    provenance of ``total_price``, for auditing

Consumers that want the pre-discount figure must read ``total_price_gross``
(or ``total_price_no_saving``) explicitly.
"""

import re
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

from .info_extractor import extract_basic_receipt_info_from_html
from .items_extractor import extract_receipt_items_from_html
from .money import to_float, to_str


def _extract_charged_total(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[str]]:
    """Read the authoritative charged total from the receipt summary.

    Lidl stamps the machine-readable ``data-receipt-total`` attribute (dotted
    decimal, e.g. "51.77") on the summary total spans.  When present it beats
    any arithmetic we could do ourselves.
    """
    for span in soup.find_all(attrs={"data-receipt-total": True}):
        value = to_float(span.get("data-receipt-total"))
        if value:
            return value, "data-receipt-total"
    return None, None


def _sum_pfand_savings(soup: BeautifulSoup) -> float:
    """Sum deposit returns (Pfandrückgabe) printed on a German receipt."""
    pfand_savings = 0.0
    try:
        purchase_list = soup.find("span", class_="purchase_list")
        if not purchase_list:
            return 0.0
        purchase_text = purchase_list.get_text()

        # Explicit "Pfandrückgabe -1,50" lines.
        for match in re.findall(r"Pfandrückgabe\s*(-?\d+,\d+)", purchase_text):
            value = to_float(match)
            if value is not None:
                pfand_savings += abs(value)

        # Otherwise look for calculation lines with a *negative* quantity —
        # deposit returns appear as e.g. "-3 x 0,25".  Positive-quantity spans
        # (regular items, kg weights like "0,248 x 3,55") must not match.
        if pfand_savings == 0:
            for qty_match, price_match in re.findall(
                r"(-\d+)\s*x\s*(\d+,\d+)", purchase_text
            ):
                qty = to_float(qty_match)
                price = to_float(price_match)
                if qty is not None and price is not None:
                    pfand_savings += abs(qty * price)
    except Exception:
        pass

    return pfand_savings


def _apply_structural_discounts(
    receipt_data: Dict[str, Any], gross: float
) -> float:
    """Populate the discount fields from the per-item discounts.

    Returns the total discount amount.
    """
    coupon_total = 0.0
    markdown_total = 0.0
    other_total = 0.0
    sticker_pcts = []

    for item in receipt_data["items"]:
        for discount in item.get("discounts") or []:
            amount = to_float(discount.get("amount"), 0.0) or 0.0
            kind = discount.get("type")
            if kind == "lidlplus_coupon":
                coupon_total += amount
            elif kind == "markdown":
                markdown_total += amount
                if discount.get("percent") is not None:
                    sticker_pcts.append(discount["percent"])
            else:
                other_total += amount

    discount_total = coupon_total + markdown_total + other_total

    receipt_data["discount_total"] = to_str(discount_total) if discount_total else None
    receipt_data["lidlplus_saved_amount"] = to_str(coupon_total) if coupon_total else None
    receipt_data["sticker_discount_amount"] = to_str(markdown_total) if markdown_total else None
    receipt_data["sticker_discount_pct"] = sticker_pcts
    # "saved_amount" has always meant the non-Lidl-Plus savings.
    regular = markdown_total + other_total
    receipt_data["saved_amount"] = to_str(regular) if regular else None

    return discount_total


def _apply_legacy_savings(
    soup: BeautifulSoup, receipt_data: Dict[str, Any]
) -> float:
    """Sum the savings found by the German text-based extraction.

    Used only when the receipt HTML carries no ``span.discount`` markup.
    """
    total_savings = 0.0

    for field in ("saved_amount", "lidlplus_saved_amount", "sticker_discount_amount"):
        value = to_float(receipt_data.get(field))
        if value:
            total_savings += value

    pfand_savings = _sum_pfand_savings(soup)
    if pfand_savings > 0:
        receipt_data["saved_pfand"] = to_str(pfand_savings)
        total_savings += pfand_savings

    return total_savings


def parse_receipt_html(
    html_content: str, receipt_id: str, receipt_date: str, total_amount: float, store: str
) -> Dict[str, Any]:
    """
    Parse receipt HTML content to extract items, discounts and totals.

    Args:
        html_content: HTML content of the receipt (from ticket.htmlPrintedReceipt)
        receipt_id: Receipt ID
        receipt_date: Receipt date
        total_amount: Total amount from API (usually 0 — the API does not
            populate it; the HTML is the real source)
        store: Store name

    Returns:
        dict: Parsed receipt data
    """
    soup = BeautifulSoup(html_content, "html.parser")

    receipt_data = extract_basic_receipt_info_from_html(
        soup, receipt_id, receipt_date, store
    )
    receipt_data["items"] = extract_receipt_items_from_html(soup)

    # Gross total = the sum of the *printed* line totals.  Recomputing from
    # quantity * unit_price drifts on weighed items (see items_extractor).
    gross = 0.0
    for item in receipt_data["items"]:
        line_total = to_float(item.get("line_total"))
        if line_total is None:
            qty = to_float(item.get("quantity"), 1.0) or 1.0
            price = to_float(item.get("price"), 0.0) or 0.0
            line_total = qty * price
        gross += line_total
    gross = round(gross, 2)

    if gross > 0:
        receipt_data["total_price_gross"] = to_str(gross)
        # Kept as an alias so existing consumers keep working.
        receipt_data["total_price_no_saving"] = to_str(gross)

    # Prefer the structural per-line discounts; fall back to the legacy
    # German text heuristics only when the receipt has no discount markup.
    has_discount_markup = bool(soup.find("span", class_="discount"))
    if has_discount_markup:
        total_savings = _apply_structural_discounts(receipt_data, gross)
    else:
        total_savings = _apply_legacy_savings(soup, receipt_data)

    # Establish what was actually charged, most trustworthy source first.
    charged, source = _extract_charged_total(soup)
    if charged is None and gross > 0:
        computed = round(gross - total_savings, 2)
        if computed > 0:
            charged, source = computed, "gross-minus-discounts"
    if charged is None and receipt_data.get("total_price"):
        # info_extractor's German "zu zahlen" line.
        charged, source = to_float(receipt_data["total_price"]), "zu-zahlen"

    if charged is not None:
        receipt_data["total_price"] = to_str(charged)
        receipt_data["total_price_source"] = source

        # Cross-check: the parsed discounts should reconcile gross to charged.
        if gross > 0 and abs((gross - total_savings) - charged) > 0.02:
            print(
                f"  Warnung: Bon {receipt_id}: Brutto {to_str(gross)} - Rabatte "
                f"{to_str(total_savings)} = {to_str(round(gross - total_savings, 2))} "
                f"weicht vom belasteten Betrag {to_str(charged)} ab"
            )

    return receipt_data
