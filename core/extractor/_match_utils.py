"""
キーワードマッチング共通ユーティリティ。
BS/PL/CF 各 extractor で共有する。
"""
import difflib
import unicodedata

# キーワードの後ろに続くと「別の勘定科目」になる文字（複合語防止）
_COMPOUND_SUFFIXES = ("原価", "費用", "費", "損失", "損", "税", "金", "率")


def matches(label: str, keywords: list[str], cutoff: float = 0.75) -> bool:
    """
    ラベルがキーワードリストのいずれかに一致するか判定する。

    修正点:
    - 「label in kw」チェックを廃止（"資産合計" が "流動資産合計" の部分文字列として
      誤マッチする問題を防止）
    - 「kw in label」チェックで、直前の文字が漢字の場合はスキップ
      （"非流動資産合計" が "流動資産" キーワードに誤マッチする問題を防止）
    """
    for kw in keywords:
        # 完全一致（最優先）
        if kw == label:
            return True

        # kw がラベルの中に含まれる場合
        if kw in label:
            idx = label.find(kw)
            # 直前の文字が漢字（CJK統合漢字）の場合はスキップ
            # 例: "非流動資産合計" の中の "流動資産" は "非" の後ろ → 別の科目
            if idx > 0 and unicodedata.category(label[idx - 1]) == 'Lo':
                continue
            # 直後に複合語を形成する文字が続く場合はスキップ
            after = label[idx + len(kw):]
            if any(after.startswith(s) for s in _COMPOUND_SUFFIXES):
                continue
            return True

    # 類似度マッチ（表記ゆれ対策）
    close = difflib.get_close_matches(label, keywords, n=1, cutoff=cutoff)
    return len(close) > 0
