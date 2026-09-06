"""
分析师一致预期 - 汇总评级、目标价分布、价格缺口与
评级历史走势。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_benchmark_bar, create_line_chart

from utils.data_service import get_analyst_consensus, get_consensus_compare
from utils.formatters import format_currency, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# 映射字典
RECO_CN = {
    "Strong Buy": "强烈买入",
    "Buy": "买入",
    "Overweight": "增持",
    "Hold": "持有",
    "Underweight": "减持",
    "Sell": "卖出",
    "Strong Sell": "强烈卖出",
}
ASSESS_CN = {
    "Bullish": "看涨",
    "Bearish": "看跌",
    "Neutral": "中性",
    "Very Bullish": "极度看涨",
    "Very Bearish": "极度看跌",
}
CONV_CN = {
    "High": "高",
    "Moderate": "中等",
    "Low": "低",
    "Very Low": "极低",
    "Very High": "极高",
}


def _section(title: str):
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1rem 0;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS.get('text_primary', '#fafafa')};
                    font-size: 0.9rem; font-weight: 600;">{title}</h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS.get('border', '#27272a')}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="分析师一致预期 | 智能金融 AI",
    page_icon=":loudspeaker:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 分析师一致预期")
st.caption("评级分布、目标价共识、历史升级降级记录与一致预期评估")

# ─── 标签页 ────────────────────────────────────────────
tab1, tab2 = st.tabs(["单只股票分析", "多只对比"])

# ─── Tab 1: 单只股票 ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = (
            st.text_input(
                "股票代码",
                value=st.session_state.get("selected_symbol", "AAPL"),
                placeholder="请输入代码（如 AAPL、MSFT、NVDA）",
                key="ac_symbol",
            )
            .strip()
            .upper()
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("分析", use_container_width=True, type="primary", key="ac_btn")

    if analyze_btn and symbol:
        st.session_state.ac_active = symbol

    active = st.session_state.get("ac_active", "")
    if active:
        with st.spinner(f"正在获取 {active} 的分析师一致预期……"):
            data = get_analyst_consensus(active)

        if "error" in data:
            st.error(f"分析失败：{data['error']}")
        else:
            st.markdown(f"### {data.get('company_name', active)} ({active})")

            # ── KPI 汇总 ──
            consensus = data.get("consensus_summary", {})
            rating = consensus.get("rating", "--")
            rating_cn = ASSESS_CN.get(rating, rating)
            target = consensus.get("target_price")
            current = data.get("current_price", 0)
            upside = consensus.get("upside_potential_pct")
            num_analysts = consensus.get("number_of_analysts", 0)
            conv = consensus.get("conviction", "")
            conv_cn = CONV_CN.get(conv, conv)

            rating_color = (
                COLORS.get("success", "#22c55e")
                if "Bullish" in (rating or "")
                else (
                    COLORS.get("danger", "#ef4444")
                    if "Bearish" in (rating or "")
                    else COLORS.get("text_muted", "#a1a1aa")
                )
            )
            upside_color = (
                COLORS.get("success", "#22c55e")
                if (upside or 0) >= 0
                else COLORS.get("danger", "#ef4444")
            )

            mcols = st.columns(5)
            with mcols[0]:
                st.metric("一致预期评级", rating_cn)
            with mcols[1]:
                st.metric(
                    "目标价均价",
                    format_currency(target) if target else "--",
                    delta=(
                        format_percent(upside) if upside is not None else None
                    ),
                    delta_color="normal" if (upside or 0) >= 0 else "inverse",
                )
            with mcols[2]:
                lo = consensus.get("target_low")
                hi = consensus.get("target_high")
                st.metric(
                    "目标价区间",
                    f"{format_currency(lo)} ~ {format_currency(hi)}"
                    if lo and hi
                    else "--",
                )
            with mcols[3]:
                st.metric("覆盖分析师数", num_analysts)
            with mcols[4]:
                st.metric("一致预期可信度", conv_cn)

            st.markdown("---")

            # ── 评级分布 + 目标价 ──
            left, right = st.columns(2)
            with left:
                _section("评级分布")
                breakdown = data.get("ratings_breakdown", {})
                if breakdown:
                    labels = list(breakdown.keys())
                    labels_cn = [RECO_CN.get(l, l) for l in labels]
                    values = list(breakdown.values())
                    # 颜色
                    colors = []
                    for l in labels:
                        if l in ("Strong Buy", "Buy", "Overweight"):
                            colors.append("#22c55e")
                        elif l in ("Strong Sell", "Sell", "Underweight"):
                            colors.append("#ef4444")
                        else:
                            colors.append("#eab308")
                    bd_df = pd.DataFrame({"评级": labels_cn, "数量": values})
                    st.bar_chart(
                        bd_df.set_index("评级"),
                        horizontal=True,
                        color=[COLORS.get("accent_primary", "#6366f1")],
                    )

            with right:
                _section("目标价对比")
                if current and target:
                    plot_df = pd.DataFrame(
                        [
                            {"项目": "当前价格", "价格 ($)": current},
                            {"项目": "目标均价", "价格 ($)": target},
                        ]
                    )
                    lo = consensus.get("target_low")
                    hi = consensus.get("target_high")
                    if lo:
                        plot_df = pd.concat(
                            [
                                pd.DataFrame([{"项目": "最低目标价", "价格 ($)": lo}]),
                                plot_df,
                            ],
                            ignore_index=True,
                        )
                    if hi:
                        plot_df = pd.concat(
                            [
                                plot_df,
                                pd.DataFrame([{"项目": "最高目标价", "价格 ($)": hi}]),
                            ],
                            ignore_index=True,
                        )
                    st.bar_chart(
                        plot_df.set_index("项目"),
                        color=[COLORS.get("accent_primary", "#6366f1")],
                    )

            st.markdown("---")

            # ── 评估说明 + 分析师建议清单 ──
            summary = data.get("summary", "")
            if summary:
                _section("一致预期评估")
                st.markdown(f"> {summary}")

            analysts = data.get("top_analysts", [])
            if analysts:
                _section("主要分析师建议")
                rows = []
                for a in analysts:
                    reco = a.get("recommendation", "")
                    rows.append(
                        {
                            "分析师/机构": a.get("analyst", ""),
                            "评级": RECO_CN.get(reco, reco),
                            "目标价": format_currency(a.get("target_price")),
                            "更新日期": a.get("date", "--"),
                        }
                    )
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── 历史变动 ──
            history = data.get("history", {})
            if history:
                _section("评级历史变化")
                hcols = st.columns(4)
                upgrades = history.get("upgrades_3m", 0)
                downgrades = history.get("downgrades_3m", 0)
                initiations = history.get("initiations_3m", 0)
                changes = history.get("total_changes_3m", 0)
                with hcols[0]:
                    st.metric("3个月内升级", upgrades)
                with hcols[1]:
                    st.metric("3个月内降级", downgrades)
                with hcols[2]:
                    st.metric("3个月内首次覆盖", initiations)
                with hcols[3]:
                    st.metric("3个月内总变动", changes)

# ─── Tab 2: 对比 ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "对比股票（以逗号分隔）",
        value="AAPL, MSFT, GOOGL, NVDA, AMZN",
        placeholder="例如 AAPL、MSFT、NVDA",
        key="ac_compare_input",
    )
    compare_btn = st.button("对比分析师一致预期", key="ac_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("请至少输入 2 只股票代码。")
        else:
            with st.spinner("正在对比各股分析师一致预期……"):
                result = get_consensus_compare(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                comparison = result.get("comparison", [])
                if comparison:
                    _section("分析师评级对比")
                    rows = []
                    for c in comparison:
                        if "error" in c:
                            continue
                        rating_en = c.get("rating", "--")
                        rows.append(
                            {
                                "代码": c.get("symbol", ""),
                                "一致预期": ASSESS_CN.get(rating_en, rating_en),
                                "目标价均价": format_currency(c.get("target_price")),
                                "当前价格": format_currency(c.get("current_price")),
                                "潜在上涨空间": format_percent(c.get("upside_potential_pct")),
                                "覆盖分析师数": c.get("number_of_analysts", 0),
                                "可信度": CONV_CN.get(c.get("conviction", ""), c.get("conviction", "")),
                            }
                        )
                    if rows:
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                    best = result.get("highest_upside", {})
                    if best:
                        st.markdown(
                            f"**潜在上涨空间最高**：{best.get('symbol', '--')} "
                            f"（{best.get('upside_potential_pct', 0):+.1f}%）"
                        )
                    most_bull = result.get("most_bullish", {})
                    if most_bull:
                        rate = most_bull.get("rating", "--")
                        st.markdown(
                            f"**最看涨一致预期**：{most_bull.get('symbol', '--')} "
                            f"（{ASSESS_CN.get(rate, rate)}）"
                        )

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "分析师一致预期来源：Yahoo Finance。目标价与评级为第三方机构发布，仅作参考，不构成投资建议。"
)
