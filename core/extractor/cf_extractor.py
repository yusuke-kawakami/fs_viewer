"""キャッシュフロー計算書 (CF) の勘定科目を抽出するモジュール。"""
from core.models.financial_data import CFData
from core.models.constants import (
    OPERATING_CF_KEYWORDS, INVESTING_CF_KEYWORDS,
    FINANCING_CF_KEYWORDS, CASH_START_KEYWORDS, CASH_END_KEYWORDS,
)
from core.extractor._match_utils import matches
from utils.number_utils import normalize_number, normalize_text


def extract_cf(
    pairs: list[tuple[str, str]],
    unit_multiplier: int = 1,
    unit: str = "円",
) -> CFData:
    data = CFData(unit=unit, unit_multiplier=unit_multiplier)

    for label, value_str in pairs:
        label_norm = normalize_text(label)
        value = normalize_number(value_str, unit_multiplier)
        if value is None:
            continue

        if matches(label_norm, OPERATING_CF_KEYWORDS, cutoff=0.72) and data.operating_cf is None:
            data.operating_cf = value
        elif matches(label_norm, INVESTING_CF_KEYWORDS, cutoff=0.72) and data.investing_cf is None:
            data.investing_cf = value
        elif matches(label_norm, FINANCING_CF_KEYWORDS, cutoff=0.72) and data.financing_cf is None:
            data.financing_cf = value
        elif matches(label_norm, CASH_START_KEYWORDS, cutoff=0.85) and data.cash_start is None:
            if "期末" not in label_norm:
                data.cash_start = value
        elif matches(label_norm, CASH_END_KEYWORDS, cutoff=0.72) and data.cash_end is None:
            if "期首" not in label_norm:
                data.cash_end = value

    return data
