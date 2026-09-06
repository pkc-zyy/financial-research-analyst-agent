"""
样式化 DataFrame 与表格渲染组件。
"""

import pandas as pd
import streamlit as st


def render_styled_dataframe(df: pd.DataFrame, highlight_column: str = None, height: int = None):
    """
    使用深色主题渲染 pandas DataFrame。

    Args:
        df: 待渲染的 DataFrame
        highlight_column: 需要按正负着色的列名（涨绿跌红）
        height: 固定高度（像素，可选）
    """
    if df.empty:
        st.caption("暂无数据。")
        return

    kwargs = {"use_container_width": True, "hide_index": True}
    if height:
        kwargs["height"] = height

    if highlight_column and highlight_column in df.columns:
        st.dataframe(
            df.style.map(
                lambda val: _color_value(val),
                subset=[highlight_column],
            ),
            **kwargs,
        )
    else:
        st.dataframe(df, **kwargs)


def render_comparison_table(data: list, highlight_symbol: str = None):
    """
    渲染同业对比表，支持对目标行高亮。

    Args:
        data: 字典列表（每一项代表一行）
        highlight_symbol: 需要加粗高亮的股票代码
    """
    if not data:
        st.caption("暂无可用的对比数据。")
        return

    df = pd.DataFrame(data)

    if highlight_symbol and "symbol" in df.columns:

        def highlight_target(row):
            if row.get("symbol") == highlight_symbol:
                return ["font-weight: 700; background-color: rgba(59, 130, 246, 0.08);"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(highlight_target, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_metrics_table(metrics: dict, title: str = ""):
    """
    Render a vertical key-value metrics table.

    Args:
        metrics: Dict of {label: value}
    """
    if title:
        st.markdown(f"**{title}**")

    if not metrics:
        st.caption("No metrics available.")
        return

    df = pd.DataFrame([{"Metric": k, "Value": v} for k, v in metrics.items()])

    st.dataframe(
        df, use_container_width=True, hide_index=True, height=min(400, len(metrics) * 38 + 40)
    )


def _color_value(val):
    """Return CSS for coloring positive/negative values."""
    try:
        v = float(str(val).replace("%", "").replace("+", "").replace("$", "").replace(",", ""))
        if v > 0:
            return "color: #10b981;"
        elif v < 0:
            return "color: #ef4444;"
    except (ValueError, TypeError):
        pass
    return ""
