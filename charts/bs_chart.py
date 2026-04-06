"""
貸借対照表 (BS) の積み上げ棒グラフ（ボックス図）を生成する。
左: 資産、右: 負債 + 純資産
"""
from typing import Optional

import plotly.graph_objects as go

from core.models.financial_data import BSData


def build_bs_chart(data: BSData) -> go.Figure:
    """BSデータから積み上げ棒グラフを生成する"""
    unit = data.unit

    # 表示用スケール
    scale, scale_label = _get_scale(data.total_assets)

    def v(x: Optional[float]) -> float:
        if x is None:
            return 0.0
        return x / scale

    # 資産側
    current = v(data.current_assets)
    fixed = v(data.fixed_assets)
    total = v(data.total_assets)
    # current + fixed が total に満たない場合は「その他資産」で補完
    other_assets = max(0.0, total - current - fixed) if total else 0.0

    # 負債・純資産側
    curr_liab = v(data.current_liabilities)
    fixed_liab = v(data.fixed_liabilities)
    equity = v(data.total_equity)
    # 合計が total_assets に満たない場合「その他」で補完（非支配株主持分等）
    other_liab = max(0.0, total - curr_liab - fixed_liab - equity) if total else 0.0

    fig = go.Figure()

    # ===== 左棒: 資産（下=固定資産、上=流動資産） =====
    if other_assets > 0.001:
        fig.add_trace(go.Bar(
            name="その他資産",
            x=["資産"],
            y=[other_assets],
            marker_color="#7FB3F5",
            text=[f"{other_assets:.1f}"],
            textposition="inside",
            textfont=dict(color="white", size=13),
            hovertemplate="その他資産: %{y:.1f}" + scale_label + "<extra></extra>",
        ))
    fig.add_trace(go.Bar(
        name="固定資産",
        x=["資産"],
        y=[fixed],
        marker_color="#1A5BBF",
        text=[f"{fixed:.1f}" if fixed else ""],
        textposition="inside",
        textfont=dict(color="white", size=13),
        hovertemplate="固定資産: %{y:.1f}" + scale_label + "<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="流動資産",
        x=["資産"],
        y=[current],
        marker_color="#4C8BF5",
        text=[f"{current:.1f}" if current else ""],
        textposition="inside",
        textfont=dict(color="white", size=13),
        hovertemplate="流動資産: %{y:.1f}" + scale_label + "<extra></extra>",
    ))

    # ===== 右棒: 負債・純資産（下=純資産、真ん中=固定負債、上=流動負債） =====
    if other_liab > 0.001:
        fig.add_trace(go.Bar(
            name="その他",
            x=["負債・純資産"],
            y=[other_liab],
            marker_color="#BDC3C7",
            text=[f"{other_liab:.1f}"],
            textposition="inside",
            textfont=dict(color="white", size=12),
            hovertemplate="その他（非支配株主持分等）: %{y:.1f}" + scale_label + "<extra></extra>",
        ))
    fig.add_trace(go.Bar(
        name="純資産",
        x=["負債・純資産"],
        y=[equity],
        marker_color="#2ECC71",
        text=[f"{equity:.1f}" if equity else ""],
        textposition="inside",
        textfont=dict(color="white", size=13),
        hovertemplate="純資産: %{y:.1f}" + scale_label + "<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="固定負債",
        x=["負債・純資産"],
        y=[fixed_liab],
        marker_color="#BF3A1A",
        text=[f"{fixed_liab:.1f}" if fixed_liab else ""],
        textposition="inside",
        textfont=dict(color="white", size=13),
        hovertemplate="固定負債: %{y:.1f}" + scale_label + "<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="流動負債",
        x=["負債・純資産"],
        y=[curr_liab],
        marker_color="#F5774C",
        text=[f"{curr_liab:.1f}" if curr_liab else ""],
        textposition="inside",
        textfont=dict(color="white", size=13),
        hovertemplate="流動負債: %{y:.1f}" + scale_label + "<extra></extra>",
    ))

    # 自己資本比率アノテーション
    eq_ratio = data.equity_ratio
    annotations = []
    if eq_ratio is not None:
        color = "#2ECC71" if eq_ratio >= 40 else ("#F39C12" if eq_ratio >= 20 else "#E74C3C")
        annotations.append(dict(
            x="負債・純資産",
            y=v(data.total_assets) * 1.05,
            text=f"<b>自己資本比率: {eq_ratio:.1f}%</b>",
            showarrow=False,
            font=dict(size=14, color=color),
            xanchor="center",
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(
            text="貸借対照表 (BS) — 財政状態",
            font=dict(size=18),
        ),
        yaxis=dict(
            title=f"金額（{scale_label}）",
            tickformat=",.0f",
        ),
        xaxis=dict(
            tickfont=dict(size=14),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        annotations=annotations,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=80, b=40, l=60, r=20),
        height=500,
    )

    return fig


def _get_scale(total_assets: Optional[float]) -> tuple[float, str]:
    """資産合計からスケールとラベルを決定する"""
    if total_assets is None:
        return 1, "円"
    if abs(total_assets) >= 1_000_000_000_000:
        return 1_000_000_000_000, "兆円"
    if abs(total_assets) >= 100_000_000:
        return 100_000_000, "億円"
    if abs(total_assets) >= 100_000:
        return 10_000, "万円"
    return 1, "円"
