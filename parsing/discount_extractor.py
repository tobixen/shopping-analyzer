"""Parse the ``<span class="discount">`` lines of a Lidl receipt.

Lidl's receipt HTML renders every discount as a pair of spans sharing a
``data-promotion-id``, printed immediately *after* the article they reduce::

    <span class="discount" data-promotion-id="100001006-BG-...">#Lidl Plus купон  #</span>
    <span class="discount" data-promotion-id="100001006-BG-...">ОТСТЪПКИ    0,24-B</span>

    <span class="discount" data-promotion-id="_DISCOUNT2">#ОТСТЪПКА 20%   #</span>
    <span class="discount" data-promotion-id="_DISCOUNT2">ОТСТЪПКИ    0,28-B</span>

The two kinds behave differently and must be kept apart:

``lidlplus_coupon``
    A Lidl Plus app coupon.  These are what the receipt footer totals up as
    "Ти спести X с Lidl Plus" / "X EUR gespart".
``markdown``
    An in-store reduction sticker (short shelf life, damaged packaging).
    Not a Lidl Plus saving and *not* included in that footer total.

This parsing is deliberately structural (CSS classes and data attributes) so
it works for every country's receipt language.
"""

import re
from typing import Any, Dict, List, Optional

from bs4 import Tag

from .money import to_float, to_str

# "ОТСТЪПКИ   0,24-B" / "Rabatt  -0,24" — the amount, however the minus sign
# and trailing tax-type letter happen to be placed.
_AMOUNT_RE = re.compile(r"(\d+[,.]\d{2})\s*-|-\s*(\d+[,.]\d{2})")
# "ОТСТЪПКА 20%" / "RABATT 20%" — the sticker percentage, when printed.
_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")


# Lidl Plus coupons carry a campaign template id, e.g.
# "100001006-BG-TEMPLATE-BGAS000038349-1".
_COUPON_ID_RE = re.compile(r"^\d+-[A-Z]{2}-TEMPLATE-")


def classify_discount(promotion_id: str, label: str) -> str:
    """Decide whether a discount is a Lidl Plus coupon, an in-store markdown or other.

    Lidl Plus is only claimed on positive evidence (the label or a coupon
    template id): an ordinary promotion such as a German "Preisvorteil" must
    not be counted as a Lidl Plus saving.
    """
    # Lidl uses synthetic "_DISCOUNT<n>" promotion ids for register-applied
    # reduction stickers.
    if promotion_id.startswith("_DISCOUNT"):
        return "markdown"
    if "lidl plus" in label.lower():
        return "lidlplus_coupon"
    if _COUPON_ID_RE.match(promotion_id):
        return "lidlplus_coupon"
    return "other"


def parse_discount_group(spans: List[Tag]) -> Optional[Dict[str, Any]]:
    """Build a single discount dict from the spans sharing one promotion id.

    Returns None when no monetary amount can be found, so that decorative or
    unparsable discount lines never silently count as a zero discount.
    """
    promotion_id = ""
    label_parts: List[str] = []
    amount_line_label = ""
    amount: Optional[float] = None

    for span in spans:
        if not promotion_id:
            promotion_id = span.get("data-promotion-id") or ""
        text = span.get_text().strip()
        match = _AMOUNT_RE.search(text)
        if match and amount is None:
            amount = to_float(match.group(1) or match.group(2))
            # Label and amount may share one span ("Preisvorteil -0,10").
            amount_line_label = text[: match.start()].strip("# ").strip()
        elif text:
            # The non-amount line carries the human-readable label, padded
            # with the '#' characters that frame boxed receipt text.
            cleaned = text.strip("#").strip()
            if cleaned:
                label_parts.append(cleaned)

    if amount is None:
        return None

    # A separate label line wins; otherwise use the text before the amount.
    label = " ".join(label_parts) or amount_line_label
    discount: Dict[str, Any] = {
        "amount": to_str(amount),
        "type": classify_discount(promotion_id, label),
        "label": label or None,
        "promotion_id": promotion_id or None,
    }

    percent_match = _PERCENT_RE.search(label)
    if percent_match:
        discount["percent"] = int(percent_match.group(1))

    return discount
