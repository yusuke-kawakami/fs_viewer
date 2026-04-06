from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BSData:
    """貸借対照表データ"""
    # 資産
    current_assets: Optional[float] = None    # 流動資産
    fixed_assets: Optional[float] = None      # 固定資産
    total_assets: Optional[float] = None      # 資産合計

    # 負債
    current_liabilities: Optional[float] = None   # 流動負債
    fixed_liabilities: Optional[float] = None     # 固定負債
    total_liabilities: Optional[float] = None     # 負債合計

    # 純資産
    total_equity: Optional[float] = None      # 純資産合計

    unit: str = "円"
    unit_multiplier: int = 1

    @property
    def equity_ratio(self) -> Optional[float]:
        """自己資本比率 (%) = 純資産合計 / 資産合計 × 100"""
        if self.total_equity and self.total_assets and self.total_assets != 0:
            return self.total_equity / self.total_assets * 100
        return None

    @property
    def is_complete(self) -> bool:
        return all([
            self.total_assets is not None,
            self.total_liabilities is not None,
            self.total_equity is not None,
        ])

    def fill_missing(self):
        """合計値から不足値を補完"""
        if self.total_assets and self.current_assets and self.fixed_assets is None:
            self.fixed_assets = self.total_assets - self.current_assets
        if self.total_assets and self.fixed_assets and self.current_assets is None:
            self.current_assets = self.total_assets - self.fixed_assets
        if self.total_liabilities and self.current_liabilities and self.fixed_liabilities is None:
            self.fixed_liabilities = self.total_liabilities - self.current_liabilities
        if self.total_liabilities and self.fixed_liabilities and self.current_liabilities is None:
            self.current_liabilities = self.total_liabilities - self.fixed_liabilities
        if self.total_assets and self.total_liabilities and self.total_equity is None:
            self.total_equity = self.total_assets - self.total_liabilities
        if self.total_equity and self.total_liabilities and self.total_assets is None:
            self.total_assets = self.total_equity + self.total_liabilities


@dataclass
class PLData:
    """損益計算書データ"""
    revenue: Optional[float] = None                   # 売上高
    cost_of_sales: Optional[float] = None             # 売上原価
    gross_profit: Optional[float] = None              # 売上総利益
    selling_admin: Optional[float] = None             # 販売費及び一般管理費
    operating_income: Optional[float] = None          # 営業利益
    ordinary_income: Optional[float] = None           # 経常利益
    pretax_income: Optional[float] = None             # 税引前当期純利益
    net_income: Optional[float] = None                # 当期純利益

    unit: str = "円"
    unit_multiplier: int = 1

    @property
    def operating_margin(self) -> Optional[float]:
        """営業利益率 (%) = 営業利益 / 売上高 × 100"""
        if self.operating_income is not None and self.revenue and self.revenue != 0:
            return self.operating_income / self.revenue * 100
        return None

    @property
    def gross_margin(self) -> Optional[float]:
        """売上総利益率 (%) = 売上総利益 / 売上高 × 100"""
        if self.gross_profit is not None and self.revenue and self.revenue != 0:
            return self.gross_profit / self.revenue * 100
        return None

    @property
    def net_margin(self) -> Optional[float]:
        """当期純利益率 (%) = 当期純利益 / 売上高 × 100"""
        if self.net_income is not None and self.revenue and self.revenue != 0:
            return self.net_income / self.revenue * 100
        return None

    @property
    def is_complete(self) -> bool:
        return self.revenue is not None and self.operating_income is not None

    def fill_missing(self):
        """段階利益の補完"""
        if self.revenue and self.cost_of_sales and self.gross_profit is None:
            self.gross_profit = self.revenue - self.cost_of_sales
        if self.gross_profit and self.selling_admin and self.operating_income is None:
            self.operating_income = self.gross_profit - self.selling_admin


@dataclass
class CFData:
    """キャッシュフロー計算書データ"""
    operating_cf: Optional[float] = None    # 営業活動によるキャッシュフロー
    investing_cf: Optional[float] = None    # 投資活動によるキャッシュフロー
    financing_cf: Optional[float] = None    # 財務活動によるキャッシュフロー
    cash_start: Optional[float] = None      # 期首現金残高
    cash_end: Optional[float] = None        # 期末現金残高

    unit: str = "円"
    unit_multiplier: int = 1

    @property
    def free_cash_flow(self) -> Optional[float]:
        """フリーキャッシュフロー = 営業CF + 投資CF"""
        if self.operating_cf is not None and self.investing_cf is not None:
            return self.operating_cf + self.investing_cf
        return None

    @property
    def pattern(self) -> tuple[Optional[str], Optional[str]]:
        """CF3区分パターン判定。(パターン名, 説明) を返す"""
        from core.models.constants import CF_PATTERNS
        if any(v is None for v in [self.operating_cf, self.investing_cf, self.financing_cf]):
            return None, None
        key = (
            self.operating_cf >= 0,
            self.investing_cf >= 0,
            self.financing_cf >= 0,
        )
        name, desc = CF_PATTERNS.get(key, ("不明", "パターンを判定できませんでした"))
        return name, desc

    @property
    def is_complete(self) -> bool:
        return all([
            self.operating_cf is not None,
            self.investing_cf is not None,
            self.financing_cf is not None,
        ])


@dataclass
class FinancialReport:
    """1つの決算書から抽出した財務三表"""
    bs: BSData = field(default_factory=BSData)
    pl: PLData = field(default_factory=PLData)
    cf: CFData = field(default_factory=CFData)
    company_name: str = ""
    fiscal_year: str = ""
    source_file: str = ""
