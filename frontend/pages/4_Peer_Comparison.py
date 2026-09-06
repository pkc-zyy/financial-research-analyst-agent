"""
同行对比 - 将股票与行业同行进行并排对比。
"""

import pandas as pd
import streamlit as st
from components.data_tables import render_comparison_table
from components.header import render_header
from components.metrics_cards import render_company_header, render_strength_weakness
from components.plotly_charts import (
    create_grouped_bar,
    create_horizontal_bar,
    create_radar_chart,
)

from utils.data_service import compare_peers
from utils.formatters import (
    format_currency,
    format_large_number,
    format_number,
    format_percent,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="同行对比 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 同行对比")
st.caption("将目标股票与行业同行并排对比")

# ─── 输入 ───────────────────────────────────────────────────
c1, c2 = st.columns([1, 2])
with c1:
    symbol = (
        st.text_input(
            "目标股票代码",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="例如：AAPL",
            key="peer_symbol",
        )
        .upper()
        .strip()
    )

with c2:
    custom_peers = st.text_input(
        "自定义同行（可选，使用英文逗号分隔）",
        placeholder="例如：MSFT, GOOGL, AMZN",
        key="custom_peers",
    )

compare_btn = st.button("开始对比", use_container_width=False, key="compare_btn")

if not symbol:
    st.info("请输入目标股票代码以开始同行对比。")
    st.stop()

if compare_btn or symbol:
    peers = None
    if custom_peers:
        peers = tuple(p.strip().upper() for p in custom_peers.split(",") if p.strip())

    with st.spinner(f"正在为 {symbol} 查找同行并对比指标……"):
        result = compare_peers(symbol, peers)

    if "error" in result:
        st.error(f"同行对比出错：{result['error']}")
        st.stop()

    # ─── 抬头 ──────────────────────────────────────────────
    peer_group = result.get("peer_group", [])
    st.markdown(
        f"**目标：** `{result.get('target', symbol)}` · **同行：** {', '.join([f'`{p}`' for p in peer_group])}"
    )

    # ─── 优势 & 风险 ──────────────────────────────
    render_strength_weakness(
        strengths=result.get("strengths", []),
        weaknesses=result.get("weaknesses", []),
    )

    st.markdown("---")

    # ─── 指标对比表 ────────────────────────────
    st.markdown("### 指标对比")

    metrics = result.get("metrics", {})
    if metrics:
        rows = []
        for sym, data in metrics.items():
            rows.append(
                {
                    "代码": sym,
                    "现价": format_currency(data.get("price")),
                    "市值": format_large_number(data.get("market_cap")),
                    "市盈率 P/E": format_number(data.get("pe_ratio")),
                    "前瞻 P/E": format_number(data.get("forward_pe")),
                    "PEG": format_number(data.get("peg_ratio")),
                    "市净率 P/B": format_number(data.get("pb_ratio")),
                    "净利率": format_percent(
                        data.get("profit_margin", 0) * 100 if data.get("profit_margin") else None
                    ),
                    "经营利润率": format_percent(
                        data.get("operating_margin", 0) * 100
                        if data.get("operating_margin")
                        else None
                    ),
                    "股本回报率 ROE": format_percent(data.get("roe", 0) * 100 if data.get("roe") else None),
                    "营收增长": format_percent(
                        data.get("revenue_growth", 0) * 100 if data.get("revenue_growth") else None
                    ),
                    "Beta 系数": format_number(data.get("beta")),
                    "行业": data.get("sector", ""),
                }
            )

        df = pd.DataFrame(rows)
        render_comparison_table(rows, highlight_symbol=symbol)

    st.markdown("---")

    # ─── 可视化对比 ──────────────────────────────────
    c1, c2 = st.columns(2)

    # 估值对比
    with c1:
        st.markdown("### 估值对比")
        val_metrics = ["pe_ratio", "pb_ratio"]
        val_labels = ["市盈率 P/E", "市净率 P/B"]

        for metric, label in zip(val_metrics, val_labels):
            syms = []
            vals = []
            colors = []
            for sym, data in metrics.items():
                v = data.get(metric)
                if v is not None:
                    syms.append(sym)
                    vals.append(v)
                    colors.append("#3b82f6" if sym == symbol else "#6b7280")

            if vals:
                fig = create_horizontal_bar(syms, vals, title=label, colors=colors)
                st.plotly_chart(fig, use_container_width=True)

    # 盈利能力雷达
    with c2:
        st.markdown("### 盈利能力画像")
        target_data = metrics.get(symbol, {})
        categories = ["净利率", "经营利润率", "ROE", "ROA", "营收增长"]
        target_vals = [
            (target_data.get("profit_margin") or 0) * 100,
            (target_data.get("operating_margin") or 0) * 100,
            (target_data.get("roe") or 0) * 100,
            (target_data.get("roa") or 0) * 100,
            (target_data.get("revenue_growth") or 0) * 100,
        ]

        # 同行中位数
        aggregates = result.get("peer_aggregates", {})
        if aggregates:
            peer_vals = [
                (aggregates.get("profit_margin", {}).get("median") or 0) * 100,
                (aggregates.get("operating_margin", {}).get("median") or 0) * 100,
                (aggregates.get("roe", {}).get("median") or 0) * 100,
                (aggregates.get("roa", {}).get("median") or 0) * 100,
                (aggregates.get("revenue_growth", {}).get("median") or 0) * 100,
            ]
            fig = create_radar_chart(
                categories,
                target_vals,
                title=f"{symbol} vs 同行中位数",
                comparison_values=peer_vals,
                comparison_label="同行中位数",
            )
        else:
            fig = create_radar_chart(categories, target_vals, title=f"{symbol} 画像")

        st.plotly_chart(fig, use_container_width=True)

    # ─── 百分位排名 ─────────────────────────────────
    rankings = result.get("percentile_rankings", {})
    if rankings:
        st.markdown("---")
        st.markdown("### 百分位排名")
        for metric, desc in rankings.items():
            metric_cn = (
                metric.replace("_", " ")
                .replace("pe ratio", "市盈率 P/E")
                .replace("pb ratio", "市净率 P/B")
                .replace("peg ratio", "PEG")
                .replace("forward pe", "前瞻 P/E")
                .replace("profit margin", "净利率")
                .replace("operating margin", "经营利润率")
                .replace("roe", "ROE")
                .replace("roa", "ROA")
                .replace("revenue growth", "营收增长")
                .replace("beta", "Beta 系数")
                .title()
            )
            st.markdown(f"- **{metric_cn}**：{desc}")

    # ─── 相对估值 ──────────────────────────────────
    rel_val = result.get("relative_valuation", {})
    if rel_val:
        st.markdown("---")
        st.markdown("### 相对估值")
        for metric, desc in rel_val.items():
            color = (
                "#10b981"
                if "discount" in str(desc).lower()
                else "#ef4444" if "premium" in str(desc).lower() else "#9ca3af"
            )
            metric_cn = metric.replace("_", " ").replace("pe", "P/E").replace("pb", "P/B").title()
            st.markdown(
                f"- **{metric_cn}**：<span style='color:{color};'>{desc}</span>",
                unsafe_allow_html=True,
            )
