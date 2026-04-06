"""
fs_viewer — 財務諸表ビューアー
決算書PDFをアップロードして財務三表（BS・PL・CF）をグラフで可視化する。

起動コマンド:
    streamlit run app.py
"""
import sys
import os

import streamlit as st

# パスを通す（モジュールimport用）
sys.path.insert(0, os.path.dirname(__file__))

from core.parser.pdf_parser import parse_pdf, PDFParseError, ScannedPDFError
from core.models.financial_data import FinancialReport, BSData, PLData, CFData
from charts.bs_chart import build_bs_chart
from charts.pl_chart import build_pl_chart
from charts.cf_chart import build_cf_chart


# ─────────────────────────────────────────────
# ページ設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="fs_viewer — 財務諸表ビューアー",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .tip-box {
        background: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 0.6rem 1rem;
        border-radius: 4px;
        font-size: 0.9rem;
        margin: 0.4rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ユーティリティ関数
# ─────────────────────────────────────────────

def _fmt(value, unit: str = "円") -> str:
    """金額をわかりやすい文字列に変換（値は常に実際の円ベース）"""
    if value is None:
        return "N/A"
    abs_v = abs(value)
    sign = "-" if value < 0 else ""
    if abs_v >= 1_000_000_000_000:
        return f"{sign}{abs_v/1_000_000_000_000:.1f}兆円"
    if abs_v >= 100_000_000:
        return f"{sign}{abs_v/100_000_000:.1f}億円"
    if abs_v >= 10_000:
        return f"{sign}{abs_v/10_000:.0f}万円"
    return f"{sign}{abs_v:,.0f}円"


def _warn_incomplete(name: str, data) -> None:
    missing = []
    if name == "BS":
        if data.total_assets is None: missing.append("資産合計")
        if data.total_liabilities is None: missing.append("負債合計")
        if data.total_equity is None: missing.append("純資産合計")
    elif name == "PL":
        if data.revenue is None: missing.append("売上高")
        if data.operating_income is None: missing.append("営業利益")
        if data.net_income is None: missing.append("当期純利益")
    elif name == "CF":
        if data.operating_cf is None: missing.append("営業CF")
        if data.investing_cf is None: missing.append("投資CF")
        if data.financing_cf is None: missing.append("財務CF")
    if missing:
        st.warning(
            f"⚠️ 以下の項目を自動抽出できませんでした: **{', '.join(missing)}**\n\n"
            "PDFのフォーマットによっては一部データが取れない場合があります。"
        )


# ─────────────────────────────────────────────
# タブ描画関数
# ─────────────────────────────────────────────

def render_bs_tab(bs: BSData) -> None:
    st.subheader("貸借対照表 (BS) — ある時点の財産目録")
    _warn_incomplete("BS", bs)

    col1, col2, col3 = st.columns(3)
    with col1:
        eq = bs.equity_ratio
        st.metric(
            "自己資本比率",
            f"{eq:.1f}%" if eq is not None else "N/A",
            help="純資産 ÷ 総資産 × 100。40%以上が安全の目安。",
        )
    with col2:
        st.metric("総資産", _fmt(bs.total_assets, bs.unit),
                  help="会社が保有する全資産の合計。")
    with col3:
        st.metric("純資産", _fmt(bs.total_equity, bs.unit),
                  help="返済不要の自己資本。厚いほど財務基盤が強固。")

    if bs.total_assets is not None:
        fig = build_bs_chart(bs)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("グラフに必要なデータが不足しています。")

    with st.expander("📚 BSの見方・分析ポイント"):
        st.markdown("""
**貸借対照表（Balance Sheet）は「ある時点での財産目録」です。**

| 左側（資産） | 右側（負債・純資産） |
|:---|:---|
| お金がどこにあるか（運用形態） | お金をどこから調達したか（調達源泉） |
| 流動資産：1年以内に現金化できる資産 | 流動負債：1年以内に返済が必要な借金 |
| 固定資産：設備・建物・投資など | 固定負債：長期借入金など |
| | 純資産：返済不要な自己資本（株主資本） |

**チェックポイント:**
- 🟢 **自己資本比率 40%以上** → 財務的に安全
- 🟡 **自己資本比率 20〜40%** → 注意が必要
- 🔴 **自己資本比率 20%未満** → 財務的に脆弱（業種による例外あり）
""")


def render_pl_tab(pl: PLData) -> None:
    st.subheader("損益計算書 (PL) — 1年間の経営成績")
    _warn_incomplete("PL", pl)

    col1, col2, col3 = st.columns(3)
    with col1:
        op_m = pl.operating_margin
        st.metric(
            "営業利益率",
            f"{op_m:.1f}%" if op_m is not None else "N/A",
            help="営業利益 ÷ 売上高 × 100。日本上場企業平均は約5%。",
        )
    with col2:
        st.metric("売上高", _fmt(pl.revenue, pl.unit), help="1年間の総売上金額。")
    with col3:
        st.metric("当期純利益", _fmt(pl.net_income, pl.unit), help="税引き後の最終的な利益。")

    if pl.revenue is not None:
        fig = build_pl_chart(pl)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("グラフに必要なデータが不足しています。")

    with st.expander("📚 PLの見方・分析ポイント"):
        st.markdown("""
**損益計算書（P/L）は「1年間の経営成績」を表します。**

売上高から段階的に費用を差し引いて最終利益が決まります：

```
売上高
  − 売上原価
────────────
  売上総利益（粗利）
  − 販売費及び一般管理費（販管費）
────────────
  営業利益  ← 本業の稼ぐ力
  ± 営業外収益・費用（受取利息・支払利息など）
────────────
  経常利益  ← 通常の事業活動の実力
  ± 特別損益（リストラ費用・資産売却益など一時的要因）
  − 法人税等
────────────
  当期純利益（最終的な儲け）
```

**チェックポイント:**
- 🟢 **営業利益率 10%以上** → 高収益企業
- 🟡 **営業利益率 5〜10%** → 日本平均レベル
- 🔴 **営業利益率 5%未満** → 収益性に課題あり
""")


def render_cf_tab(cf: CFData) -> None:
    st.subheader("キャッシュフロー計算書 (CF) — 1年間の現金の動き")
    _warn_incomplete("CF", cf)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("営業CF", _fmt(cf.operating_cf, cf.unit),
                  help="本業で稼いだ（使った）現金。プラスが基本。")
    with col2:
        st.metric("投資CF", _fmt(cf.investing_cf, cf.unit),
                  help="設備投資・M&Aなどに使った現金。成長企業はマイナスが多い。")
    with col3:
        st.metric("財務CF", _fmt(cf.financing_cf, cf.unit),
                  help="借入・返済・配当などの現金の動き。")
    with col4:
        fcf = cf.free_cash_flow
        st.metric("フリーCF", _fmt(fcf, cf.unit),
                  help="営業CF + 投資CF。企業が自由に使える現金の創出力。")

    pattern_name, pattern_desc = cf.pattern
    if pattern_name:
        st.info(f"**CFパターン: {pattern_name}**　— {pattern_desc}")

    if cf.is_complete:
        fig = build_cf_chart(cf)
        st.plotly_chart(fig, use_container_width=True)
    elif not any([cf.operating_cf, cf.investing_cf, cf.financing_cf]):
        st.info(
            "💡 **CF計算書が見つかりませんでした。**\n\n"
            "考えられる理由:\n"
            "- 四半期決算短信でCF計算書の作成が省略されている（よくあるケース）\n"
            "- PDFのフォーマットが未対応\n\n"
            "通期の有価証券報告書や決算短信ではCF計算書が掲載される場合があります。"
        )
    else:
        st.warning("グラフに必要なデータが不足しています。")

    with st.expander("📚 CFの見方・分析ポイント"):
        st.markdown("""
**キャッシュフロー計算書は「1年間の現金の動き」を追います。**

| 区分 | 内容 | 健全な状態 |
|:---|:---|:---|
| 営業CF | 本業で稼いだ現金 | **プラス**（本業で稼げている） |
| 投資CF | 設備投資・M&Aなど | マイナスが多い（積極投資） |
| 財務CF | 借入・返済・配当 | 状況により異なる |

**フリーキャッシュフロー（FCF）= 営業CF + 投資CF**
企業の「真の稼ぐ力」を示す重要指標。

**CFパターンの代表例:**
| パターン | 営業CF | 投資CF | 財務CF | 意味 |
|:---|:---:|:---:|:---:|:---|
| 優良企業型 | ＋ | − | − | 本業で稼いで投資・借入返済 |
| 積極投資型 | ＋ | − | ＋ | 借入して成長投資を加速 |
| ベンチャー型 | − | − | ＋ | 赤字でも投資・資金調達継続 |
""")


def render_welcome() -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
<div class="tip-box">
<b>🏦 BS（貸借対照表）</b><br>
ある時点での財産状態を<br>
積み上げ棒グラフで表示。<br>
自己資本比率を算出。
</div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
<div class="tip-box">
<b>📈 PL（損益計算書）</b><br>
1年間の収益構造を<br>
ウォーターフォールチャートで表示。<br>
営業利益率を算出。
</div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
<div class="tip-box">
<b>💰 CF（キャッシュフロー）</b><br>
現金の流れを棒グラフで表示。<br>
FCF・CFパターン判定を表示。
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
### 使い方
1. **上のファイルアップローダー**から決算書PDFをアップロード
2. 自動解析後、**BS・PL・CF** タブでグラフを確認
3. 各タブの「📚 見方・分析ポイント」で学習

### 対応ファイル
- TDNet 決算短信（四半期・通期）
- EDINET 有価証券報告書（PDF形式）
- テキスト埋め込みPDFのみ対応（スキャン画像PDFは非対応）

> ⚠️ 本アプリは学習・参考目的です。投資判断はご自身の責任でお願いします。
""")


# ─────────────────────────────────────────────
# メインフロー
# ─────────────────────────────────────────────

st.markdown("## 📊 fs_viewer — 財務諸表ビューアー")
st.markdown("決算書PDFをアップロードすると、BS・PL・CFを自動でグラフ化します。")

# セッション初期化
if "report" not in st.session_state:
    st.session_state.report = None
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None

# アップロードウィジェット
uploaded = st.file_uploader(
    "決算書PDFをアップロード（TDNet 決算短信 / EDINET 有価証券報告書）",
    type=["pdf"],
    help="テキスト形式のPDFに対応しています。スキャン画像PDFは非対応です。",
)

if uploaded is not None:
    if st.session_state.last_filename != uploaded.name:
        st.session_state.report = None
        st.session_state.last_filename = uploaded.name

        with st.spinner(f"「{uploaded.name}」を解析中..."):
            try:
                file_bytes = uploaded.read()
                report = parse_pdf(file_bytes, filename=uploaded.name)
                st.session_state.report = report
            except ScannedPDFError as e:
                st.error(
                    f"⚠️ **スキャンPDF検出**\n\n{e}\n\n"
                    "**対処法**: EDINETまたはTDNetからテキスト形式のPDFをダウンロードしてください。"
                )
            except PDFParseError as e:
                st.error(f"❌ **解析エラー**\n\n{e}")
            except Exception as e:
                st.error(f"❌ **予期しないエラー**\n\n{str(e)}")

report: FinancialReport = st.session_state.report

if report is not None:
    # 会社情報バナー
    info_parts = []
    if report.company_name:
        info_parts.append(f"**{report.company_name}**")
    if report.fiscal_year:
        info_parts.append(report.fiscal_year)

    col_info, col_btn = st.columns([5, 1])
    with col_info:
        if info_parts:
            st.info("　".join(info_parts))
    with col_btn:
        if st.button("🔄 リセット"):
            st.session_state.report = None
            st.session_state.last_filename = None
            st.rerun()

    st.divider()

    tab_bs, tab_pl, tab_cf = st.tabs([
        "🏦 貸借対照表 (BS)",
        "📈 損益計算書 (PL)",
        "💰 キャッシュフロー (CF)",
    ])
    with tab_bs:
        render_bs_tab(report.bs)
    with tab_pl:
        render_pl_tab(report.pl)
    with tab_cf:
        render_cf_tab(report.cf)

elif uploaded is None:
    render_welcome()
