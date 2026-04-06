"""
pdfplumberを使ったPDF解析メインモジュール。
BS/PL/CFの各ページからテーブルを抽出する。
"""
import io
from typing import Optional

import pdfplumber

from core.parser.statement_classifier import classify_pages, detect_unit_from_pages
from core.parser.table_cleaner import (
    clean_table, merge_multipage_tables,
    is_side_by_side_bs, split_side_by_side_bs,
    extract_label_value_pairs, extract_pairs_from_text,
)
from core.models.financial_data import FinancialReport, BSData, PLData, CFData
from core.extractor.bs_extractor import extract_bs
from core.extractor.pl_extractor import extract_pl
from core.extractor.cf_extractor import extract_cf


class PDFParseError(Exception):
    pass


class ScannedPDFError(PDFParseError):
    pass


def parse_pdf(file_bytes: bytes, filename: str = "") -> FinancialReport:
    """
    PDFバイト列から財務三表を抽出してFinancialReportを返す。

    Raises:
        ScannedPDFError: スキャンPDFで文字が抽出できない場合
        PDFParseError: パース失敗時
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise PDFParseError(f"PDFを開けませんでした: {e}")

    with pdf:
        # スキャンチェック
        _check_not_scanned(pdf)

        # ページ分類
        page_map = classify_pages(pdf)

        report = FinancialReport(source_file=filename)

        # 会社名・決算期を推定（先頭ページから）
        report.company_name, report.fiscal_year = _detect_company_info(pdf)

        # BS抽出
        if page_map["bs"]:
            mult, unit = detect_unit_from_pages(pdf, page_map["bs"])
            pairs = _extract_pairs_from_pages(pdf, page_map["bs"], is_bs=True)
            report.bs = extract_bs(pairs, unit_multiplier=mult, unit=unit)

        # PL抽出
        if page_map["pl"]:
            mult, unit = detect_unit_from_pages(pdf, page_map["pl"])
            pairs = _extract_pairs_from_pages(pdf, page_map["pl"], is_pl=True)
            report.pl = extract_pl(pairs, unit_multiplier=mult, unit=unit)

        # CF抽出
        if page_map["cf"]:
            mult, unit = detect_unit_from_pages(pdf, page_map["cf"])
            pairs = _extract_pairs_from_pages(pdf, page_map["cf"], is_pl=True)
            report.cf = extract_cf(pairs, unit_multiplier=mult, unit=unit)

    return report


def _check_not_scanned(pdf: pdfplumber.PDF):
    """先頭3ページをチェックしてスキャンPDFか判定する"""
    total_chars = 0
    pages_checked = min(3, len(pdf.pages))
    for i in range(pages_checked):
        try:
            text = pdf.pages[i].extract_text() or ""
            total_chars += len(text)
        except Exception:
            pass
    if total_chars < 50:
        raise ScannedPDFError(
            "このPDFは画像（スキャン）PDFのようです。"
            "テキスト形式のPDFをご使用ください。"
        )


def _extract_pairs_from_pages(
    pdf: pdfplumber.PDF,
    page_indices: list[int],
    is_bs: bool = False,
    is_pl: bool = False,
) -> list[tuple[str, str]]:
    """指定ページ群のテーブルを結合して (ラベル, 値) ペアリストを返す"""
    all_tables = []
    all_text_pairs = []

    for idx in page_indices:
        if idx >= len(pdf.pages):
            continue
        page = pdf.pages[idx]

        # テキストベース抽出（常に実行してフォールバックとして保持）
        try:
            page_text = page.extract_text() or ""
            text_pairs = extract_pairs_from_text(page_text)
            all_text_pairs.extend(text_pairs)
        except Exception:
            pass

        # テーブルベース抽出
        tables = _extract_tables_resilient(page)
        for tbl in tables:
            cleaned = clean_table(tbl)
            if cleaned:
                all_tables.append(cleaned)

    # BS/PL/CF はテキスト抽出を優先
    # （BS: 合計行ラベル欠落、PL/CF: セクションヘッダー行によるインデックスズレ対策）
    if is_bs or is_pl:
        if all_text_pairs:
            return all_text_pairs
        # テキストが取れなければテーブルにフォールバック

    # テーブルベース結果を優先、ペア数が少なければテキストベースで補完
    if all_tables:
        merged = merge_multipage_tables(all_tables)

        if is_bs and is_side_by_side_bs(merged):
            left, right = split_side_by_side_bs(merged)
            pairs = extract_label_value_pairs(left)
            pairs += extract_label_value_pairs(right)
        else:
            pairs = extract_label_value_pairs(merged)

        # テーブル抽出で十分なペアが取れた場合はそれを返す
        meaningful = [(l, v) for l, v in pairs if v]
        if len(meaningful) >= 3:
            return pairs

    # フォールバック: テキストベース結果を返す
    return all_text_pairs


def _extract_tables_resilient(page) -> list:
    """複数の戦略でテーブル抽出を試みる"""
    # 戦略1: デフォルト設定
    tables = page.extract_tables()
    if tables and _looks_valid(tables[0]):
        return tables

    # 戦略2: 水平線のみ（罫線が横だけのPDF）
    try:
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,
        })
        if tables and _looks_valid(tables[0]):
            return tables
    except Exception:
        pass

    # 戦略3: テキストベース（罫線なしPDF）
    try:
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 3,
            "min_words_vertical": 2,
        })
        if tables and _looks_valid(tables[0]):
            return tables
    except Exception:
        pass

    # 戦略4: テキストから直接行を構築
    return _text_fallback(page)


def _looks_valid(table: list) -> bool:
    """テーブルが有効そうか簡易チェック"""
    if not table or len(table) < 3:
        return False
    non_empty_rows = sum(1 for row in table if any(c for c in row if c))
    return non_empty_rows >= 3


def _text_fallback(page) -> list:
    """テキスト抽出フォールバック: 行ごとにスペースで分割"""
    try:
        text = page.extract_text() or ""
        rows = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # スペースで列を分割
            parts = line.rsplit(None, 2)  # 末尾の数値を分離
            if len(parts) >= 2:
                rows.append(parts)
        if rows:
            return [rows]
    except Exception:
        pass
    return []


def _detect_company_info(pdf: pdfplumber.PDF) -> tuple[str, str]:
    """先頭ページから会社名と決算期を推定する"""
    import re
    company = ""
    fiscal_year = ""

    if not pdf.pages:
        return company, fiscal_year

    try:
        text = pdf.pages[0].extract_text() or ""
    except Exception:
        return company, fiscal_year

    # 決算期の検出（例: 2024年3月期, 第85期）
    m = re.search(r"\d{4}年\d{1,2}月期", text)
    if m:
        fiscal_year = m.group(0)
    else:
        m = re.search(r"第\d+期", text)
        if m:
            fiscal_year = m.group(0)

    # 会社名の推定（最初の行から）
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        # 「株式会社」「㈱」を含む行を探す
        for line in lines[:10]:
            if "株式会社" in line or "㈱" in line or "（株）" in line:
                company = line
                break
        if not company and lines:
            company = lines[0]

    return company, fiscal_year
