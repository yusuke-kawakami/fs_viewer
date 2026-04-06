import re
import unicodedata
from typing import Optional


def normalize_number(raw: str, unit_multiplier: int = 1) -> Optional[float]:
    """
    日本語財務諸表の数値文字列を float に変換する。

    対応フォーマット:
      - △1,234 / ▲1,234  → 負数
      - (1,234)           → 負数
      - 全角数字 １，２３４ → half-width に正規化
      - 単位倍率を適用
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in ("-", "—", "―", "－", "‐", "…", "※", ""):
        return None

    # 全角→半角正規化
    s = unicodedata.normalize("NFKC", s)

    # 負数判定
    negative = False
    if s.startswith("△") or s.startswith("▲") or s.startswith("▽"):
        negative = True
        s = s[1:]
    elif s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    elif s.startswith("−") or s.startswith("-"):
        negative = True
        s = s[1:]

    # カンマ・スペース除去
    s = s.replace(",", "").replace("，", "").replace(" ", "").replace("\u3000", "")

    # 残った記号を除去（単位「百万円」などが混入した場合）
    s = re.sub(r"[^\d.]", "", s)

    if not s:
        return None

    try:
        value = float(s) * unit_multiplier
        return -value if negative else value
    except ValueError:
        return None


def detect_unit_multiplier(text: str) -> int:
    """
    ページテキストから金額単位を検出して倍率を返す。
    （百万円 → 1_000_000, 千円 → 1_000, 円 → 1）
    """
    if "百万円" in text:
        return 1_000_000
    if "千円" in text:
        return 1_000
    return 1


def detect_unit_label(text: str) -> str:
    """金額単位のラベル文字列を返す"""
    if "百万円" in text:
        return "百万円"
    if "千円" in text:
        return "千円"
    return "円"


def format_amount(value: Optional[float], unit: str = "百万円") -> str:
    """グラフ表示用の数値フォーマット"""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.1f}兆円"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f}億円"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.1f}万円"
    return f"{value:,.0f}円"


def normalize_text(text: str) -> str:
    """全角・半角正規化 + 前後空白除去"""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()
