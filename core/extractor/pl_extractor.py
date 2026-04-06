"""損益計算書 (PL) の勘定科目を抽出するモジュール。"""
from core.models.financial_data import PLData
from core.models.constants import (
    REVENUE_KEYWORDS, COST_OF_SALES_KEYWORDS, GROSS_PROFIT_KEYWORDS,
    SELLING_ADMIN_KEYWORDS, OPERATING_INCOME_KEYWORDS,
    ORDINARY_INCOME_KEYWORDS, PRETAX_INCOME_KEYWORDS, NET_INCOME_KEYWORDS,
)
from core.extractor._match_utils import matches
from utils.number_utils import normalize_number, normalize_text


def extract_pl(
    pairs: list[tuple[str, str]],
    unit_multiplier: int = 1,
    unit: str = "円",
) -> PLData:
    data = PLData(unit=unit, unit_multiplier=unit_multiplier)

    for label, value_str in pairs:
        label_norm = normalize_text(label)
        value = normalize_number(value_str, unit_multiplier)
        if value is None:
            continue

        if matches(label_norm, REVENUE_KEYWORDS) and data.revenue is None:
            data.revenue = value
        elif matches(label_norm, COST_OF_SALES_KEYWORDS) and data.cost_of_sales is None:
            data.cost_of_sales = value
        elif matches(label_norm, GROSS_PROFIT_KEYWORDS) and data.gross_profit is None:
            data.gross_profit = value
        elif matches(label_norm, SELLING_ADMIN_KEYWORDS) and data.selling_admin is None:
            data.selling_admin = value
        elif matches(label_norm, OPERATING_INCOME_KEYWORDS) and data.operating_income is None:
            data.operating_income = value
        elif matches(label_norm, ORDINARY_INCOME_KEYWORDS) and data.ordinary_income is None:
            data.ordinary_income = value
        elif matches(label_norm, PRETAX_INCOME_KEYWORDS) and data.pretax_income is None:
            data.pretax_income = value
        elif matches(label_norm, NET_INCOME_KEYWORDS) and data.net_income is None:
            data.net_income = value

    data.fill_missing()
    return data
