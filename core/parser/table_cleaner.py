"""
pdfplumberで抽出した生テーブルを正規化・クリーニングする。
"""
import re
import unicodedata
from typing import Optional


def clean_table(raw_table: list[list[Optional[str]]]) -> list[list[str]]:
    """
    生テーブルの各セルをクリーニングして返す（改行を保持）。
    - None → ""
    - 全角/半角正規化
    - 先頭・末尾の空白除去
    """
    cleaned = []
    for row in raw_table:
        if row is None:
            continue
        clean_row = []
        for cell in row:
            if cell is None:
                clean_row.append("")
            else:
                s = str(cell)
                s = unicodedata.normalize("NFKC", s)
                s = s.replace("\r", "").strip()
                clean_row.append(s)
        if any(c for c in clean_row):
            cleaned.append(clean_row)
    return cleaned


def expand_multiline_rows(table: list[list[str]]) -> list[list[str]]:
    """
    1セルに改行区切りで複数の勘定科目が詰め込まれている行を展開する。
    複数の値列がある場合は「増減列（▲が多い列）」を除外して当期実績列を選択する。

    例: row = ["売上高\n売上原価\n営業利益", "1000\n500\n200"]
    → [["売上高","1000"], ["売上原価","500"], ["営業利益","200"]]
    """
    expanded = []
    for row in table:
        if not row:
            continue
        label_cell = row[0]
        has_newline = "\n" in label_cell

        if has_newline:
            labels = [l.strip() for l in label_cell.split("\n") if l.strip()]
            # 値列を適切に選択（増減▲列を除外）
            value_cell = _pick_best_value_cell(row[1:]) if len(row) > 1 else ""
            if "\n" in value_cell:
                values = [v.strip() for v in value_cell.split("\n") if v.strip()]
            else:
                values = _split_number_sequence(value_cell)

            for i, label in enumerate(labels):
                val = values[i] if i < len(values) else ""
                expanded.append([label, val])
        else:
            expanded.append(row)
    return expanded


def _pick_best_value_cell(value_cells: list[str]) -> str:
    """
    複数の値セルから当期実績値のセルを選択する。

    ロジック:
    - 最後のセルが「増減列」（▲/△が多数含まれる）の場合はスキップ
    - 残った中で最後のセルを返す（＝当期末または当期累計）
    """
    cells = [c for c in value_cells if c.strip()]
    if not cells:
        return ""
    if len(cells) == 1:
        return cells[0]

    # 末尾の増減列を取り除く
    # 判定基準: セル内の行のうち40%以上が△▲で始まる場合は増減列とみなす
    while len(cells) > 1:
        last = cells[-1]
        lines = [l.strip() for l in last.split('\n') if l.strip()]
        if not lines:
            cells.pop()
            continue
        delta_count = sum(
            1 for l in lines
            if l.startswith('▲') or l.startswith('△') or l.startswith('▽')
        )
        if delta_count / len(lines) >= 0.4:
            cells.pop()
        else:
            break

    return cells[-1] if cells else ""


def merge_multipage_tables(tables_list: list[list[list[str]]]) -> list[list[str]]:
    """
    複数ページにまたがる表を結合する。
    ヘッダー行（最初の行）が重複している場合は2ページ目以降のヘッダーをスキップ。
    """
    if not tables_list:
        return []
    if len(tables_list) == 1:
        return tables_list[0]

    merged = tables_list[0][:]
    first_header = tables_list[0][0] if tables_list[0] else []

    for tbl in tables_list[1:]:
        if not tbl:
            continue
        start_idx = 1 if tbl[0] == first_header else 0
        merged.extend(tbl[start_idx:])
    return merged


def split_side_by_side_bs(table: list[list[str]]) -> tuple[list[list[str]], list[list[str]]]:
    """
    BS特有の左右並列レイアウトを分割する。
    左: 資産, 右: 負債・純資産
    """
    if not table or len(table[0]) < 4:
        return table, []

    n_cols = len(table[0])
    mid = n_cols // 2
    left, right = [], []
    for row in table:
        left_row = row[:mid]
        right_row = row[mid:]
        if any(c for c in left_row):
            left.append(left_row)
        if any(c for c in right_row):
            right.append(right_row)
    return left, right


def is_side_by_side_bs(table: list[list[str]]) -> bool:
    asset_kw = {"資産", "流動資産", "固定資産"}
    liab_kw = {"負債", "流動負債", "固定負債", "純資産"}
    for row in table[:5]:
        row_text = " ".join(row)
        if any(kw in row_text for kw in asset_kw) and any(kw in row_text for kw in liab_kw):
            return True
    return False


def extract_label_value_pairs(table: list[list[str]]) -> list[tuple[str, str]]:
    """
    テーブルから (勘定科目名, 金額) のペアリストを抽出する。
    複数列がある場合は最新年度の実績値（増減△列はスキップ）を使用。
    """
    # まず改行を含む行を展開
    table = expand_multiline_rows(table)

    pairs = []
    skip_labels = {"前期", "当期", "前年度", "当年度",
                   "前連結会計年度", "当連結会計年度", "期首", "期末"}
    for row in table:
        if len(row) < 2:
            continue
        label = row[0].strip().replace("\n", " ")
        if not label or label in skip_labels:
            continue

        value_str = _pick_current_period_value(row[1:])
        pairs.append((label, value_str))
    return pairs


def _pick_current_period_value(value_cells: list[str]) -> str:
    """
    単一行の複数数値セルから当期実績値を選択する。
    増減▲列を末尾から除外し、残りの最後（当期）を返す。
    """
    numeric_cells = [c.strip() for c in value_cells if c.strip() and re.search(r'\d', c)]
    if not numeric_cells:
        return ""

    # 末尾の増減▲セルを除去
    while len(numeric_cells) > 1:
        last = numeric_cells[-1]
        if last.startswith('△') or last.startswith('▲') or last.startswith('▽'):
            numeric_cells.pop()
        else:
            break

    return numeric_cells[-1]


def extract_pairs_from_text(page_text: str) -> list[tuple[str, str]]:
    """
    ページテキストを行ごとにスキャンして (ラベル, 値) ペアを抽出する。

    列選択ロジック:
      - 行末の△▲数値（増減列）は除外
      - 残りが3列以上: 2番目（当期実績）を選択
      - 残りが2列: 最後（当期）を選択
      - ラベルに混入した先行数値を除去
    """
    pairs = []
    num_re = re.compile(r'([△▲▽]?[\d,]+(?:\.\d+)?)')
    # ラベルの末尾にある数値（前期比較値が混入する場合）を除去するパターン
    label_trailing_num = re.compile(r'\s+[\d,]+\s*$')

    # スキップ対象行の判定パターン
    # - 目次行: 「…」3文字以上連続、または ".....5文字以上"
    # - 注記行: "(注)" / "（注）" で始まる行（ページ参照が含まれる）
    skip_re = re.compile(r'[…]{3,}|\.{5,}')
    note_prefix_re = re.compile(r'^[（(]注[)）]')

    for line in page_text.split('\n'):
        line = line.strip()
        if len(line) < 3:
            continue
        # 目次行・注記行はスキップ
        if skip_re.search(line) or note_prefix_re.match(line):
            continue

        all_matches = list(num_re.finditer(line))
        if not all_matches:
            continue

        # 末尾の△▲（増減列）を除去
        # 3列以上の場合のみ除去（2列前期/当期で当期が△の場合を保持するため）
        filtered = all_matches[:]
        while len(filtered) > 2 and (
            filtered[-1].group(1).startswith('△') or
            filtered[-1].group(1).startswith('▲') or
            filtered[-1].group(1).startswith('▽')
        ):
            filtered.pop()

        if not filtered:
            continue

        # 2列: 最後の値を使用（当期）
        # 3列以上: 2番目の値を使用（左から: 期首|当期末|増減 の場合、当期末が2番目）
        if len(filtered) >= 3:
            chosen = filtered[1]   # 2番目 = 当期末
        else:
            chosen = filtered[-1]  # 最後 = 当期

        value = chosen.group(1)

        # ラベル: chosen より前のテキスト、末尾の数値は除去
        label = line[:chosen.start()].strip()
        label = label_trailing_num.sub('', label).strip()

        if label and not re.match(r'^[\d,△▲\s]+$', label):
            pairs.append((label, value))
    return pairs


# ─── 内部ユーティリティ ───────────────────────────

def _split_number_sequence(text: str) -> list[str]:
    """
    スペース区切りの数値列を分割する。
    例: "1,000 ▲500 300" → ["1,000", "▲500", "300"]
    """
    return re.findall(r'[△▲▽]?[\d,]+(?:\.\d+)?', text)
