"""Tests for per-line discount extraction and net/gross totals.

Lidl receipts render discounts as ``<span class="discount">`` pairs that
directly follow the article they apply to:

    <span class="article"   data-art-id="..." ...>4,000 x 1,32</span>
    <span class="article"   data-art-id="..." ...>БИСКВИТИ КАКАО   5,28 B</span>
    <span class="discount"  data-promotion-id="100001000-BG-...">#Lidl Plus купон  #</span>
    <span class="discount"  data-promotion-id="100001000-BG-...">ОТСТЪПКИ    1,32-B</span>

Before the fix these spans were ignored entirely, so every couponed receipt
was booked at its gross total.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bs4 import BeautifulSoup

from parsing.items_extractor import extract_receipt_items_from_html
from parsing.receipt_parser import parse_receipt_html


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# Faithful excerpt of the markup Lidl Bulgaria returns (receipt
# 030001928220260721182207, 2026-07-21, Лидл Варна 192).  Three Lidl Plus
# coupons plus one in-store 20% markdown sticker; the last item is sold by
# weight so its printed line total (2,37) differs from qty*unit_price
# (2,398 * 0,99 = 2,374).
BG_RECEIPT_WITH_DISCOUNTS = """
<span class="purchase_list"><span id="purchase_list_line_1" class="article" data-art-id="7201094" data-art-quantity="4,0" data-unit-price="1,32" data-tax-type="B" data-art-description="БИСКВИТИ КАКАО">4,000 x 1,32                  </span>
<span id="purchase_list_line_2" class="article" data-art-id="7201094" data-art-quantity="4,0" data-unit-price="1,32" data-tax-type="B" data-art-description="БИСКВИТИ КАКАО">БИСКВИТИ КАКАО                        5,28 B</span>
<span id="purchase_list_line_3" class="discount" data-promotion-id="100001000-BG-TEMPLATE-BGSD000439939-1">#Lidl Plus купон                #</span>
<span id="purchase_list_line_4" class="discount" data-promotion-id="100001000-BG-TEMPLATE-BGSD000439939-1">ОТСТЪПКИ                              1,32-B</span>
<span id="purchase_list_line_5" class="article" data-art-id="0022751" data-art-quantity="2,0" data-unit-price="2,04" data-tax-type="B" data-art-description="ГАУДА НАРЯЗАН">2,000 x 2,04                  </span>
<span id="purchase_list_line_6" class="article" data-art-id="0022751" data-art-quantity="2,0" data-unit-price="2,04" data-tax-type="B" data-art-description="ГАУДА НАРЯЗАН">ГАУДА НАРЯЗАН                         4,08 B</span>
<span id="purchase_list_line_7" class="discount" data-promotion-id="100001006-BG-TEMPLATE-BGAS000038349-1">#Lidl Plus купон                #</span>
<span id="purchase_list_line_8" class="discount" data-promotion-id="100001006-BG-TEMPLATE-BGAS000038349-1">ОТСТЪПКИ                              0,82-B</span>
<span id="purchase_list_line_9" class="article" data-art-id="7201353" data-art-quantity="2,0" data-unit-price="0,81" data-tax-type="B" data-art-description="КИСЕЛО КРАВЕ МЛЯКО">2,000 x 0,81                  </span>
<span id="purchase_list_line_10" class="article" data-art-id="7201353" data-art-quantity="2,0" data-unit-price="0,81" data-tax-type="B" data-art-description="КИСЕЛО КРАВЕ МЛЯКО">КИСЕЛО КРАВЕ МЛЯКО                    1,62 B</span>
<span id="purchase_list_line_11" class="discount" data-promotion-id="100001006-BG-TEMPLATE-BGAS000155979-1">#Lidl Plus купон                #</span>
<span id="purchase_list_line_12" class="discount" data-promotion-id="100001006-BG-TEMPLATE-BGAS000155979-1">ОТСТЪПКИ                              0,24-B</span>
<span id="purchase_list_line_13" class="discount" data-promotion-id="_DISCOUNT2">#ОТСТЪПКА 20%                   #</span>
<span id="purchase_list_line_14" class="discount" data-promotion-id="_DISCOUNT2">ОТСТЪПКИ                              0,28-B</span>
<span id="purchase_list_line_15" class="article" data-art-id="0082491" data-art-quantity="2,398" data-unit-price="0,99" data-tax-type="B" data-art-description="ДЕЛИКАТЕСЕН ПЪПЕШ">2,398 x 0,99                  </span>
<span id="purchase_list_line_16" class="article" data-art-id="0082491" data-art-quantity="2,398" data-unit-price="0,99" data-tax-type="B" data-art-description="ДЕЛИКАТЕСЕН ПЪПЕШ">ДЕЛИКАТЕСЕН ПЪПЕШ                     2,37 B</span>
</span><span class="purchase_summary"><span id="purchase_summary_2">МЕЖДИННА СУМА                        10,69</span>
<span id="purchase_summary_4" data-receipt-total="10.69" data-promotion-id="">ОБЩА СУМА                            10,69</span>
<span id="purchase_summary_9" data-tender-description="КРЕДИТНА/ДЕБИТНА КАРТА">КРЕДИТНА/ДЕБИТНА КАРТ                10,69</span>
</span><span class="crm_information"><span id="crm_information_3">#     Ти спести 2,38 евро с Lidl Plus!     #</span>
</span>
"""

# A receipt with no discounts at all — net must equal gross.
BG_RECEIPT_NO_DISCOUNTS = """
<span class="purchase_list">
<span class="article" data-art-id="0001230" data-unit-price="1,68" data-tax-type="B" data-art-description="КОРНФЛЕЙКС">КОРНФЛЕЙКС                            1,68 B</span>
<span class="article" data-art-id="7208885" data-unit-price="8,18" data-tax-type="B" data-art-description="АДАНА КЕБАП">АДАНА КЕБАП                           8,18 B</span>
</span><span class="purchase_summary">
<span id="purchase_summary_4" data-receipt-total="9.86" data-promotion-id="">ОБЩА СУМА                             9,86</span>
</span>
"""


# The same article can be rung up on two separate lines (a second bottle
# grabbed after other items, or two weighings of loose fruit).  Each printed
# line is its own item — merging them silently drops one line's money.
BG_RECEIPT_REPEATED_ARTICLE = """
<span class="purchase_list">
<span class="article" data-art-id="0044142" data-unit-price="1,02" data-tax-type="B" data-art-description="ST.BREW КРАФТ БИРА">ST.BREW КРАФТ БИРА                    1,02 B</span>
<span class="article" data-art-id="0009913" data-unit-price="1,43" data-tax-type="B" data-art-description="ПРЯСНО МЛЯКО 3%">ПРЯСНО МЛЯКО 3%                       1,43 B</span>
<span class="article" data-art-id="0044142" data-unit-price="1,02" data-tax-type="B" data-art-description="ST.BREW КРАФТ БИРА">ST.BREW КРАФТ БИРА                    1,02 B</span>
</span><span class="purchase_summary">
<span id="purchase_summary_4" data-receipt-total="3.47" data-promotion-id="">ОБЩА СУМА                             3,47</span>
</span>
"""


def _by_name(items):
    return {item["name"]: item for item in items}


# --------------------------------------------------------------------------
# items_extractor: per-line discounts
# --------------------------------------------------------------------------


def test_discount_spans_are_attached_to_preceding_item():
    """Each discount must be linked to the article line it applies to."""
    items = _by_name(extract_receipt_items_from_html(make_soup(BG_RECEIPT_WITH_DISCOUNTS)))

    assert [d["amount"] for d in items["БИСКВИТИ КАКАО"]["discounts"]] == ["1,32"]
    assert [d["amount"] for d in items["ГАУДА НАРЯЗАН"]["discounts"]] == ["0,82"]
    # This item carries a coupon *and* a separate in-store markdown
    assert [d["amount"] for d in items["КИСЕЛО КРАВЕ МЛЯКО"]["discounts"]] == [
        "0,24",
        "0,28",
    ]
    assert items["ДЕЛИКАТЕСЕН ПЪПЕШ"]["discounts"] == []


def test_discount_type_distinguishes_coupon_from_markdown():
    """Lidl Plus coupons and in-store markdowns behave differently downstream."""
    items = _by_name(extract_receipt_items_from_html(make_soup(BG_RECEIPT_WITH_DISCOUNTS)))
    milk = items["КИСЕЛО КРАВЕ МЛЯКО"]["discounts"]

    assert milk[0]["type"] == "lidlplus_coupon"
    assert milk[0]["promotion_id"] == "100001006-BG-TEMPLATE-BGAS000155979-1"
    assert milk[1]["type"] == "markdown"
    assert milk[1]["promotion_id"] == "_DISCOUNT2"
    assert milk[1]["percent"] == 20


def test_item_line_total_uses_printed_amount_not_recomputed():
    """Weighed items round per line; qty*unit_price would give 2,374 not 2,37."""
    items = _by_name(extract_receipt_items_from_html(make_soup(BG_RECEIPT_WITH_DISCOUNTS)))
    assert items["ДЕЛИКАТЕСЕН ПЪПЕШ"]["line_total"] == "2,37"


def test_item_net_total_is_line_total_minus_discounts():
    items = _by_name(extract_receipt_items_from_html(make_soup(BG_RECEIPT_WITH_DISCOUNTS)))
    milk = items["КИСЕЛО КРАВЕ МЛЯКО"]
    assert milk["line_total"] == "1,62"
    assert milk["discount_total"] == "0,52"
    assert milk["net_total"] == "1,10"


def test_items_without_discounts_get_empty_discount_fields():
    items = extract_receipt_items_from_html(make_soup(BG_RECEIPT_NO_DISCOUNTS))
    for item in items:
        assert item["discounts"] == []
        assert item["discount_total"] is None
        assert item["net_total"] == item["line_total"]


# --------------------------------------------------------------------------
# receipt_parser: receipt-level totals
# --------------------------------------------------------------------------


def test_receipt_totals_net_gross_and_discount():
    """total_price is what was charged; total_price_gross is before discounts."""
    result = parse_receipt_html(
        BG_RECEIPT_WITH_DISCOUNTS, "r1", "2026.07.21", 0.0, "Лидл Варна 192"
    )
    assert result["total_price"] == "10,69"
    assert result["total_price_gross"] == "13,35"
    assert result["discount_total"] == "2,66"


def test_total_price_no_saving_stays_gross_for_backwards_compatibility():
    result = parse_receipt_html(
        BG_RECEIPT_WITH_DISCOUNTS, "r1", "2026.07.21", 0.0, "Лидл Варна 192"
    )
    assert result["total_price_no_saving"] == result["total_price_gross"]


def test_coupon_and_markdown_totals_are_reported_separately():
    result = parse_receipt_html(
        BG_RECEIPT_WITH_DISCOUNTS, "r1", "2026.07.21", 0.0, "Лидл Варна 192"
    )
    # 1,32 + 0,82 + 0,24 — matches the receipt's "Ти спести 2,38" footer
    assert result["lidlplus_saved_amount"] == "2,38"
    # the 20% sticker is NOT a Lidl Plus saving
    assert result["sticker_discount_amount"] == "0,28"
    assert result["sticker_discount_pct"] == [20]


def test_charged_total_matches_receipt_total_attribute():
    """data-receipt-total is authoritative and must win over any summing."""
    result = parse_receipt_html(
        BG_RECEIPT_WITH_DISCOUNTS, "r1", "2026.07.21", 0.0, "Лидл Варна 192"
    )
    assert result["total_price"] == "10,69"
    assert result["total_price_source"] == "data-receipt-total"


def test_repeated_article_stays_two_separate_lines():
    """Grouping by article id across the whole receipt would lose a line."""
    items = extract_receipt_items_from_html(make_soup(BG_RECEIPT_REPEATED_ARTICLE))
    beers = [i for i in items if i["name"] == "ST.BREW КРАФТ БИРА"]
    assert len(beers) == 2, "the two beer lines were merged into one"
    assert [b["line_total"] for b in beers] == ["1,02", "1,02"]


def test_repeated_article_counted_twice_in_gross():
    result = parse_receipt_html(
        BG_RECEIPT_REPEATED_ARTICLE, "r3", "2026.05.24", 0.0, "Лидл Варна"
    )
    # 1,02 + 1,43 + 1,02 — matches the receipt's own total
    assert result["total_price_gross"] == "3,47"


def test_receipt_without_discounts_has_equal_net_and_gross():
    result = parse_receipt_html(
        BG_RECEIPT_NO_DISCOUNTS, "r2", "2026.07.21", 0.0, "Лидл Варна 192"
    )
    assert result["total_price"] == "9,86"
    assert result["total_price_gross"] == "9,86"
    assert result["discount_total"] is None


# --------------------------------------------------------------------------
# Review fixes (2026-10-11)
# --------------------------------------------------------------------------

# The same article scanned twice in a row: two printed lines, two items.
BG_RECEIPT_ADJACENT_REPEAT = """
<span class="purchase_list">
<span class="article" data-art-id="0044142" data-unit-price="1,02" data-tax-type="B" data-art-description="ST.BREW КРАФТ БИРА">ST.BREW КРАФТ БИРА                    1,02 B</span>
<span class="article" data-art-id="0044142" data-unit-price="1,02" data-tax-type="B" data-art-description="ST.BREW КРАФТ БИРА">ST.BREW КРАФТ БИРА                    1,02 B</span>
</span><span class="purchase_summary">
<span id="purchase_summary_4" data-receipt-total="2.04" data-promotion-id="">ОБЩА СУМА                             2,04</span>
</span>
"""

# Synthetic German layout, modelled on what the legacy parser expects: the
# line total alone in a css_bold span, a deposit return as a negative line,
# a Preisvorteil discount with label and amount in one span, and only the
# printed "zu zahlen" total (no data-receipt-total).
DE_RECEIPT = """
<span class="purchase_list">
<span class="article" data-art-id="1001" data-unit-price="1,49" data-art-description="Mineralwasser">Mineralwasser</span><span class="article css_bold" data-art-id="1001" data-unit-price="1,49" data-art-description="Mineralwasser">1,49</span>
<span class="discount" data-promotion-id="X1">Preisvorteil -0,10</span>
<span class="article" data-art-id="9001" data-art-quantity="-3" data-unit-price="0,25" data-art-description="Pfandrückgabe">-3 x 0,25</span><span class="article css_bold" data-art-id="9001" data-art-quantity="-3" data-unit-price="0,25" data-art-description="Pfandrückgabe">-0,75</span>
<span class="article" data-art-id="1002" data-unit-price="2,00" data-art-description="Brot">Brot</span><span class="article css_bold" data-art-id="1002" data-unit-price="2,00" data-art-description="Brot">2,00</span>
<span class="discount" data-promotion-id="200001000-DE-TEMPLATE-DESD0001-1">Lidl Plus Rabatt -0,50</span>
</span><span class="purchase_summary">
<span><span id="purchase_summary_1">zu zahlen</span><span class="css_bold">2,14</span></span>
</span>
"""


def test_adjacent_repeat_is_two_items():
    items = extract_receipt_items_from_html(make_soup(BG_RECEIPT_ADJACENT_REPEAT))
    assert [i["line_total"] for i in items] == ["1,02", "1,02"]
    data = parse_receipt_html(BG_RECEIPT_ADJACENT_REPEAT, "r", "2026-01-01", 0, "s")
    assert data["total_price_gross"] == "2,04"


def test_negative_line_total_keeps_its_sign():
    items = _by_name(extract_receipt_items_from_html(make_soup(DE_RECEIPT)))
    assert items["Pfandrückgabe"]["line_total"] == "-0,75"


def test_german_receipt_totals_and_classification():
    data = parse_receipt_html(DE_RECEIPT, "r", "2026-01-01", 0, "s")
    items = _by_name(data["items"])
    assert data["total_price_gross"] == "2,74"
    assert data["total_price"] == "2,14"
    assert data["total_price_source"] == "zu-zahlen"
    assert data["saved_pfand"] == "0,75"
    water = items["Mineralwasser"]["discounts"][0]
    assert water["type"] == "other"
    assert water["label"] == "Preisvorteil"
    bread = items["Brot"]["discounts"][0]
    assert bread["type"] == "lidlplus_coupon"
    assert data["lidlplus_saved_amount"] == "0,50"
    assert data["saved_amount"] == "0,10"


def test_unknown_promotion_is_not_counted_as_lidl_plus():
    from parsing.discount_extractor import classify_discount
    assert classify_discount("X1", "Preisvorteil") == "other"
    assert classify_discount("", "") == "other"
    assert classify_discount("100001000-BG-TEMPLATE-BGSD000439939-1", "") == "lidlplus_coupon"
    assert classify_discount("_DISCOUNT2", "ОТСТЪПКА 20%") == "markdown"


def test_printed_total_beats_arithmetic_without_receipt_total():
    html = DE_RECEIPT.replace('<span class="css_bold">2,14</span>', '<span class="css_bold">2,20</span>')
    data = parse_receipt_html(html, "r", "2026-01-01", 0, "s")
    assert data["total_price"] == "2,20"
    assert data["total_price_source"] == "zu-zahlen"


def test_legacy_sticker_discount_counted_once():
    from parsing.receipt_parser import _apply_legacy_savings
    receipt = {"saved_amount": "0,30", "sticker_discount_amount": 0.30,
               "lidlplus_saved_amount": "1,00"}
    assert round(_apply_legacy_savings(make_soup("<span></span>"), receipt, 0.0), 2) == 1.30


def test_discount_before_first_article_is_reported(capsys):
    html = """<span class="purchase_list">
<span class="discount" data-promotion-id="_DISCOUNT1">ОТСТЪПКИ    0,10-B</span>
<span class="article" data-art-id="1" data-unit-price="1,00" data-art-description="A">A    1,00 B</span>
</span>"""
    items = extract_receipt_items_from_html(make_soup(html))
    assert items[0]["discounts"] == []
    assert "0,10" in capsys.readouterr().out


def test_discount_outside_purchase_list_is_not_attributed():
    html = """<span class="purchase_list">
<span class="article" data-art-id="1" data-unit-price="1,00" data-art-description="A">A    1,00 B</span>
</span><span class="purchase_summary">
<span class="discount" data-promotion-id="_DISCOUNT9">ОТСТЪПКИ    0,50-B</span>
</span>"""
    items = extract_receipt_items_from_html(make_soup(html))
    assert items[0]["discounts"] == []
