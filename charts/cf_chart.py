"""
キャッシュフロー計算書 (CF) のウォーターフォール（ブリッジ）チャートを生成する。
期首残高 → 営業CF → 投資CF → 財務CF → 期末残高
"""
from typing import Optional

import plotly.graph_objects as go

from core.models.financial_data import CFData


def build_cf_chart(data: CFData) -> go.Figure:
    """CFデータを期首〜期末ブリッジ（ウォーターフォール）で表示"""
    scale, scale_label = _get_scale(data)

    def v(x: Optional[float]) -> Optional[float]:
        if x is None:
            return None
        return x / scale

    cash_start = v(data.cash_start)
    op  = v(data.operating_cf)
    inv = v(data.investing_cf)
    fin = v(data.financing_cf)
    cash_end = v(data.cash_end)
    fcf = v(data.free_cash_flow)

    x_labels = []
    y_values = []
    measures = []
    texts    = []
    hover    = []

    # 期首残高（absolute ベース）
    if cash_start is not None:
        x_labels.append("期首残高")
        y_values.append(cash_start)
        measures.append("absolute")
        texts.append(f"{cash_start:.2f}")
        hover.append(f"期首残高: {cash_start:.2f}{scale_label}<br>期初の現金残高")

    # 営業CF（relative）
    if op is not None:
        x_labels.append("営業CF")
        y_values.append(op)
        measures.append("relative")
        texts.append(f"{op:+.2f}")
        hover.append(f"営業CF: {op:+.2f}{scale_label}<br>本業で稼いだ現金")

    # 投資CF（relative）
    if inv is not None:
        x_labels.append("投資CF")
        y_values.append(inv)
        measures.append("relative")
        texts.append(f"{inv:+.2f}")
        hover.append(f"投資CF: {inv:+.2f}{scale_label}<br>設備投資・M&Aなど")

    # 財務CF（relative）
    if fin is not None:
        x_labels.append("財務CF")
        y_values.append(fin)
        measures.append("relative")
        texts.append(f"{fin:+.2f}")
        hover.append(f"財務CF: {fin:+.2f}{scale_label}<br>借入・返済・配当")

    # 期末残高（total = 集計値）
    if cash_end is not None:
        x_labels.append("期末残高")
        y_values.append(cash_end)
        measures.append("total")
        texts.append(f"{cash_end:.2f}")
        hover.append(f"期末残高: {cash_end:.2f}{scale_label}<br>期末の現金残高")

    if not x_labels:
        fig = go.Figure()
        fig.add_annotation(
            text="データを抽出できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False, font=dict(size=16),
        )
        return fig

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=x_labels,
        y=y_values,
        text=texts,
        textposition="outside",
        textfont=dict(size=13),
        connector=dict(line=dict(color="#888", width=1, dash="dot")),
        increasing=dict(marker=dict(color="#2ECC71")),   # 増加: 緑
        decreasing=dict(marker=dict(color="#E74C3C")),   # 減少: 赤
        totals=dict(marker=dict(color="#95A5A6")),       # 残高: グレー
        hovertext=hover,
        hoverinfo="text",
    ))

    # FCFアノテーション
    annotations = []
    if fcf is not None:
        color = "#27AE60" if fcf >= 0 else "#C0392B"
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.01, y=0.99,
            text=f"<b>フリーCF: {fcf:+.2f}{scale_label}</b>（営業CF + 投資CF）",
            showarrow=False,
            font=dict(size=13, color=color),
            xanchor="left", yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=color, borderwidth=1,
        ))

    # CFパターン
    pattern_name, pattern_desc = data.pattern
    if pattern_name:
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.5, y=-0.18,
            text=f"<b>CFパターン: {pattern_name}</b><br>"
                 f"<span style='font-size:11px'>{pattern_desc}</span>",
            showarrow=False,
            font=dict(size=12),
            xanchor="center", yanchor="top",
            bgcolor="rgba(240,240,255,0.9)",
            bordercolor="#aaa", borderwidth=1,
        ))

    fig.update_layout(
        title=dict(text="キャッシュフロー計算書 (CF) — 現金の動き", font=dict(size=18)),
        yaxis=dict(
            title=f"金額（{scale_label}）",
            tickformat=",.2f",
        ),
        xaxis=dict(tickfont=dict(size=14)),
        showlegend=False,
        annotations=annotations,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=80, b=100, l=70, r=20),
        height=520,
    )

    return fig


def _get_scale(data: CFData) -> tuple[float, str]:
    vals = [
        abs(x) for x in [
            data.operating_cf, data.investing_cf, data.financing_cf,
            data.cash_start, data.cash_end,
        ]
        if x is not None
    ]
    max_val = max(vals) if vals else 0
    if max_val >= 1_000_000_000_000:
        return 1_000_000_000_000, "兆円"
    if max_val >= 100_000_000:
        return 100_000_000, "億円"
    if max_val >= 100_000:
        return 10_000, "万円"
    return 1, "円"
