"""
市场颠覆分析 - 评估公司的创新与颠覆潜力，并进行多公司对比。
"""

import pandas as pd
import streamlit as st
from components.data_tables import render_styled_dataframe
from components.header import render_header
from components.metrics_cards import render_score_badge, render_strength_weakness
from components.plotly_charts import (
    create_gauge_chart,
    create_grouped_bar,
    create_horizontal_bar,
)

from utils.data_service import analyze_disruption, compare_disruption
from utils.formatters import format_currency, format_large_number, format_number
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="市场颠覆分析 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 市场颠覆分析")
st.caption("评估公司的创新能力与颠覆潜力")

# ─── 模式切换 ─────────────────────────────────────────────
mode = st.radio(
    "模式", ["单公司分析", "多公司对比"], horizontal=True, label_visibility="collapsed"
)

if mode == "单公司分析":
    # ─── 单公司分析 ─────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    with c1:
        symbol = (
            st.text_input(
                "股票代码",
                value=st.session_state.get("selected_symbol", "NVDA"),
                placeholder="例如：NVDA",
                key="disruption_symbol",
            )
            .upper()
            .strip()
        )
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("分析颠覆潜力", use_container_width=True)

    if not symbol:
        st.info("请输入股票代码以分析其颠覆画像。")
        st.stop()

    if analyze or symbol:
        with st.spinner(f"正在为 {symbol} 分析颠覆画像……"):
            result = analyze_disruption(symbol)

        if "error" in result:
            st.error(f"错误：{result['error']}")
            st.stop()

        # 公司抬头
        st.markdown(
            f"**{result.get('name', symbol)}** · "
            f"{result.get('sector', '')} · {result.get('industry', '')} · "
            f"市值：{format_large_number(result.get('financial_summary', {}).get('market_cap'))}"
        )

        st.markdown("---")

        # ─── 颠覆分数展示 ───────────────────────────
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            score = result.get("disruption_score", 0)
            classification = result.get("classification", "Unknown")

            # 分类徽章样式
            cls_map = {
                "Active Disruptor": "disruptor",
                "Moderate Innovator": "innovator",
                "Stable Incumbent": "incumbent",
                "At Risk": "at-risk",
            }
            cls_cn_map = {
                "Active Disruptor": "积极颠覆者",
                "Moderate Innovator": "稳健创新者",
                "Stable Incumbent": "在位稳健者",
                "At Risk": "风险型企业",
            }
            badge_cls = cls_map.get(classification, "neutral")
            cls_cn = cls_cn_map.get(classification, classification)

            fig = create_gauge_chart(
                value=score,
                title="颠覆得分",
                ranges=[
                    {"range": [0, 30], "color": "rgba(239, 68, 68, 0.25)"},
                    {"range": [30, 50], "color": "rgba(245, 158, 11, 0.25)"},
                    {"range": [50, 70], "color": "rgba(59, 130, 246, 0.25)"},
                    {"range": [70, 100], "color": "rgba(16, 185, 129, 0.25)"},
                ],
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(
                f'<div style="text-align: center;"><span class="classification-badge {badge_cls}">{cls_cn}</span></div>',
                unsafe_allow_html=True,
            )
            desc = result.get("classification_description", "")
            if desc:
                st.caption(desc)

        # ─── 分数构成 ────────────────────────────────
        st.markdown("---")
        st.markdown("### 分数构成")

        components_data = result.get("score_components", {})
        weights = result.get("score_weights", {})

        c1, c2, c3 = st.columns(3)

        with c1:
            rd_score = components_data.get("rd_score", 0)
            weight = weights.get("rd_intensity", 0.35)
            fig = create_gauge_chart(rd_score, f"研发强度 ({weight*100:.0f}%)", height=200)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            growth_score = components_data.get("growth_score", 0)
            weight = weights.get("revenue_acceleration", 0.40)
            fig = create_gauge_chart(
                growth_score, f"营收增长加速度 ({weight*100:.0f}%)", height=200
            )
            st.plotly_chart(fig, use_container_width=True)

        with c3:
            margin_score = components_data.get("margin_score", 0)
            weight = weights.get("margin_trajectory", 0.25)
            fig = create_gauge_chart(
                margin_score, f"利润率趋势 ({weight*100:.0f}%)", height=200
            )
            st.plotly_chart(fig, use_container_width=True)

        # ─── 量化信号 ────────────────────────────
        st.markdown("---")
        st.markdown("### 量化信号")

        signals = result.get("quantitative_signals", {})

        # 研发强度
        rd = signals.get("rd_intensity", {})
        if rd:
            with st.expander("研发强度 R&D", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("研发/营收比", rd.get("rd_to_revenue_ratio", "N/A"))
                trend = rd.get("trend", "N/A")
                trend_cn = (
                    "上升" if "rising" in str(trend).lower() or "up" in str(trend).lower()
                    else "下降" if "falling" in str(trend).lower() or "down" in str(trend).lower()
                    else "稳定"
                )
                c2.metric("趋势", trend_cn)
                c3.metric("对比行业倍数", rd.get("vs_industry_multiple", "N/A"))

                # 研发趋势图
                ratios = rd.get("rd_ratios_by_year", [])
                if ratios:
                    fig = create_horizontal_bar(
                        labels=[f"第 {i+1} 年" for i in range(len(ratios))],
                        values=[r * 100 for r in ratios],
                        title="各年研发/营收比 (%)",
                        colors=["#3b82f6"] * len(ratios),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = rd.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # 营收加速度
        rev = signals.get("revenue_acceleration", {})
        if rev:
            with st.expander("营收加速度", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("同比增长率", rev.get("yoy_growth", "N/A"))
                c2.metric("复合增长率 CAGR", rev.get("cagr", "N/A"))
                trajectory = rev.get("trajectory", "N/A")
                traj_cn = (
                    "加速" if "accel" in str(trajectory).lower()
                    else "减速" if "decel" in str(trajectory).lower()
                    else trajectory
                )
                c3.metric("发展轨迹", traj_cn)

                growth_rates = rev.get("growth_rates_by_year", [])
                if growth_rates:
                    colors = ["#10b981" if g >= 0 else "#ef4444" for g in growth_rates]
                    fig = create_horizontal_bar(
                        labels=[f"第 {i+1} 年" for i in range(len(growth_rates))],
                        values=[g * 100 for g in growth_rates],
                        title="各年营收增长率 (%)",
                        colors=colors,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = rev.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # 利润率趋势
        margin = signals.get("gross_margin_trajectory", {})
        if margin:
            with st.expander("毛利率走势", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("当前毛利率", margin.get("current_gross_margin", "N/A"))
                c2.metric("当前经营利润率", margin.get("current_operating_margin", "N/A"))
                trend = margin.get("trend", "N/A")
                trend_cn = (
                    "扩张" if "expand" in str(trend).lower()
                    else "收缩" if "contract" in str(trend).lower()
                    else "稳定" if "stable" in str(trend).lower() else trend
                )
                c3.metric("趋势", trend_cn)

                gm_by_year = margin.get("gross_margins_by_year", [])
                if gm_by_year:
                    fig = create_horizontal_bar(
                        labels=[f"第 {i+1} 年" for i in range(len(gm_by_year))],
                        values=[g * 100 for g in gm_by_year],
                        title="各年毛利率 (%)",
                        colors=["#8b5cf6"] * len(gm_by_year),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                assessment = margin.get("assessment", "")
                if assessment:
                    st.info(assessment)

        # ─── 优势 & 风险因素 ────────────────────────
        st.markdown("---")
        render_strength_weakness(
            strengths=result.get("strengths", []),
            weaknesses=result.get("risk_factors", []),
        )

else:
    # ─── 对比模式 ────────────────────────────────
    st.markdown("### 颠覆画像对比")

    symbols_input = st.text_input(
        "输入股票代码（英文逗号分隔，2-10 个）",
        placeholder="例如：NVDA, MSFT, AAPL, AMZN",
        key="disruption_compare_input",
    )

    if symbols_input:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

        if len(symbols) < 2:
            st.warning("至少输入 2 个股票代码才能对比。")
            st.stop()

        with st.spinner("正在对比多家公司的颠覆画像……"):
            result = compare_disruption(tuple(symbols))

        if "error" in result:
            st.error(f"错误：{result['error']}")
            st.stop()

        comparison = result.get("comparison", [])
        if comparison:
            # 对比表格
            df = pd.DataFrame(comparison)
            column_cn = {
                "symbol": "代码",
                "name": "名称",
                "industry": "行业",
                "disruption_score": "颠覆得分",
                "classification": "分类",
                "rd_intensity": "研发强度",
                "revenue_growth": "营收增长",
                "margin_trend": "利润率趋势",
            }
            column_order = [
                "symbol",
                "name",
                "industry",
                "disruption_score",
                "classification",
                "rd_intensity",
                "revenue_growth",
                "margin_trend",
            ]
            existing_cols = [c for c in column_order if c in df.columns]
            df = df[existing_cols]
            df = df.sort_values("disruption_score", ascending=False)
            df_cn = df.rename(columns=column_cn)

            st.dataframe(df_cn, use_container_width=True, hide_index=True)

            # 可视化对比
            if len(comparison) > 0:
                labels = [c.get("symbol", "?") for c in comparison]
                scores = [c.get("disruption_score", 0) for c in comparison]
                # 按得分排序
                sorted_pairs = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
                labels, scores = zip(*sorted_pairs)

                colors = []
                for s in scores:
                    if s >= 70:
                        colors.append("#10b981")
                    elif s >= 50:
                        colors.append("#3b82f6")
                    elif s >= 30:
                        colors.append("#f59e0b")
                    else:
                        colors.append("#ef4444")

                fig = create_horizontal_bar(
                    list(labels),
                    list(scores),
                    title="颠覆得分排名",
                    colors=list(colors),
                )
                st.plotly_chart(fig, use_container_width=True)

            most = result.get("most_disruptive")
            if most:
                st.success(f"最具颠覆力的公司：**{most}**")
    else:
        st.info("请在上方输入以英文逗号分隔的股票代码以进行颠覆画像对比。")
