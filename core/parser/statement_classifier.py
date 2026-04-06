"""
PDFの各ページを走査して、BS/PL/CFのページ番号を特定する。
"""
from typing import TYPE_CHECKING

from core.models.constants import BS_MARKERS, PL_MARKERS, CF_MARKERS
from utils.number_utils import normalize_text

if TYPE_CHECKING:
    import pdfplumber


def classify_pages(pdf: "pdfplumber.PDF") -> dict[str, list[int]]:
    """
    各ページのテキストを走査してBS/PL/CFのページ番号リストを返す。

    Returns:
        {'bs': [2, 3], 'pl': [4], 'cf': [5, 6]}
        見つからない場合は空リスト。
    """
    result = {"bs": [], "pl": [], "cf": []}

    for i, page in enumerate(pdf.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue

        text_norm = normalize_text(text)

        if _contains_any(text_norm, BS_MARKERS):
            result["bs"].append(i)
        if _contains_any(text_norm, PL_MARKERS):
            result["pl"].append(i)
        if _contains_any(text_norm, CF_MARKERS):
            result["cf"].append(i)

    return result


def _contains_any(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False


def detect_unit_from_pages(pdf: "pdfplumber.PDF", page_indices: list[int]) -> tuple[int, str]:
    """指定ページ群からユニット倍率を検出する"""
    from utils.number_utils import detect_unit_multiplier, detect_unit_label
    for idx in page_indices:
        if idx >= len(pdf.pages):
            continue
        try:
            text = pdf.pages[idx].extract_text() or ""
        except Exception:
            continue
        if "百万円" in text or "千円" in text:
            return detect_unit_multiplier(text), detect_unit_label(text)
    return 1, "円"
