"""貸借対照表 (BS) の勘定科目を抽出するモジュール。"""
from core.models.financial_data import BSData
from core.models.constants import (
    CURRENT_ASSETS_KEYWORDS, FIXED_ASSETS_KEYWORDS, TOTAL_ASSETS_KEYWORDS,
    CURRENT_LIAB_KEYWORDS, FIXED_LIAB_KEYWORDS, TOTAL_LIAB_KEYWORDS,
    TOTAL_EQUITY_KEYWORDS,
)
from core.extractor._match_utils import matches
from utils.number_utils import normalize_number, normalize_text


def extract_bs(
    pairs: list[tuple[str, str]],
    unit_multiplier: int = 1,
    unit: str = "円",
) -> BSData:
    data = BSData(unit=unit, unit_multiplier=unit_multiplier)

    for label, value_str in pairs:
        label_norm = normalize_text(label)
        value = normalize_number(value_str, unit_multiplier)
        if value is None:
            continue

        # cutoff=0.90: "有形固定資産合計"(類似度0.857)が"固定資産合計"に誤マッチしないよう厳格化
        if matches(label_norm, CURRENT_ASSETS_KEYWORDS, cutoff=0.90) and data.current_assets is None:
            data.current_assets = value
        elif matches(label_norm, FIXED_ASSETS_KEYWORDS, cutoff=0.90) and data.fixed_assets is None:
            data.fixed_assets = value
        elif matches(label_norm, TOTAL_ASSETS_KEYWORDS, cutoff=0.90) and data.total_assets is None:
            data.total_assets = value
        elif matches(label_norm, CURRENT_LIAB_KEYWORDS, cutoff=0.90) and data.current_liabilities is None:
            data.current_liabilities = value
        elif matches(label_norm, FIXED_LIAB_KEYWORDS, cutoff=0.90) and data.fixed_liabilities is None:
            data.fixed_liabilities = value
        elif matches(label_norm, TOTAL_LIAB_KEYWORDS, cutoff=0.90) and data.total_liabilities is None:
            data.total_liabilities = value
        elif matches(label_norm, TOTAL_EQUITY_KEYWORDS, cutoff=0.90) and data.total_equity is None:
            data.total_equity = value

    data.fill_missing()
    return data
