"""
損益計算書 (PL) の段階棒グラフを生成する。
全バーを0ベースラインに揃えた段階表示:
売上高 → 売上総利益 → 営業利益 → 経常利益 → 当期純利益
"""
from typing import Optional

import plotly.graph_objects as go

from core.models.financial_data import PLData


# 各段階の色定義
_COLORS = {
    "売上高":           "#4C8BF5",   # 青
    "売上総利益":       "#E67E22",   # オレンジ
    "営業利益":         "#E74C3C",   # 赤
    "経常利益":         "#8E44AD",   # 紫
    "税引前当期純利益": "#C0392B",   # 濃赤
    "当期純利益":       "#27AE60",   # 緑（利益）
    "当期純損失":       "#922B21",   # 暗赤（損失）
}


def build_pl_chart(data: PLData) -> go.Figure:
    """PLデータから0ベースライン段階棒グラフを生成する"""
    scale, scale_label = _get_scale(data.revenue)

    def v(x: Optional[float]) -> Optional[float]:
        if x is None:
            return None
        return x / scale

    rev    = v(data.revenue)
    gross  = v(data.gross_profit)
    op     = v(data.operating_income)
    ord_i  = v(data.ordinary_income)
    pretax = v(data.pretax_income)
    net    = v(data.net_income)

    # gross が None でも補完
    if gross is None and rev is not None and data.cost_of_sales is not None:
        gross = rev - data.cost_of_sales / scale

    # 表示する段階を収集（None は除外）
    stages = []
    if rev is not None:
        stages.append(("売上高", rev))
    if gross is not None:
        stages.append(("売上総利益", gross))
    if op is not None:
        stages.append(("営業利益", op))
    if ord_i is not None:
        stages.append(("経常利益", ord_i))
    if pretax is not None:
        stages.append(("税引前当期純利益", pretax))
    if net is not None:
        label = "当期純利益" if net >= 0 else "当期純損失"
        stages.append((label, net))

    if not stages:
        fig = go.Figure()
        fig.add_annotation(
            text="データを抽出できませんでした",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16),
        )
        return fig

    x_labels = [s[0] for s in stages]
    y_values = [s[1] for s in stages]
    colors   = [_COLORS.get(s[0], "#95A5A6") for s in stages]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels,
        y=y_values,
        marker_color=colors,
        text=[f"{y:.2f}" for y in y_values],
        textposition="outside",
        textfont=dict(size=13),
        hovertemplate="%{x}: %{y:.2f}" + scale_label + "<extra></extra>",
        width=0.55,
    ))

    # 営業利益率アノテーション
    annotations = []
    op_margin = data.operating_margin
    if op_margin is not None:
        color = "#2ECC71" if op_margin >= 10 else ("#F39C12" if op_margin >= 5 else "#E74C3C")
        annotations.append(dict(
            xref="paper", yref="paper",
            x=0.01, y=0.99,
            text=f"<b>営業利益率: {op_margin:.1f}%</b>（日本上場企業平均: 約5%）",
            showarrow=False,
            font=dict(size=13, color=color),
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor=color,
            borderwidth=1,
        ))

    # y軸レンジを少し余裕を持たせてバーのラベルが見切れないように
    max_val = max(abs(y) for y in y_values) if y_values else 1
    min_val = min(y for y in y_values)
    y_max = max_val * 1.2
    y_min = min(0, min_val * 1.2)

    fig.update_layout(
        title=dict(text="損益計算書 (PL) — 収益構造", font=dict(size=18)),
        yaxis=dict(
            title=f"金額（{scale_label}）",
            tickformat=",.2f",
            range=[y_min, y_max],
        ),
        xaxis=dict(tickfont=dict(size=13)),
        annotations=annotations,
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=80, b=40, l=70, r=20),
        height=500,
    )

    return fig


def _get_scale(revenue: Optional[float]) -> tuple[float, str]:
    if revenue is None:
        return 1, "円"
    if abs(revenue) >= 1_000_000_000_000:
        return 1_000_000_000_000, "兆円"
    if abs(revenue) >= 100_000_000:
        return 100_000_000, "億円"
    if abs(revenue) >= 100_000:
        return 10_000, "万円"
    return 1, "円"
