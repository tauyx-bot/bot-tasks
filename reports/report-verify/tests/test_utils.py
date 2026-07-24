from decimal import Decimal

from scripts.utils import decimal_value, masked_name_matches, normalize


def test_normalize_full_width_and_inequality():
    assert normalize(" ＜ 0.4（mg/m3） ") == "<0.4(mg/m3)"


def test_decimal_preserves_numeric_part():
    assert decimal_value("<0.003") == Decimal("0.003")


def test_masked_chinese_name():
    assert masked_name_matches("伍*天", "伍玉天")
    assert masked_name_matches("吕*", "吕丰")
