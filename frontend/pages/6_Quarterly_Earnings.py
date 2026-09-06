"""
季度财报分析 - EPS 跟踪、超预期/不及预期模式、财报质量评分。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.metrics_cards import render_score_badge
from components.plotly_charts import (
    create_earnings_surprise_chart,
    create_gauge_chart,
    create_horizontal_bar,
)

from utils.data_service import analyze_earnings, compare_earnings
from utils.formatters import (
    format_currency,
    format_date,
    format_large_number,
    format_number,
    format_percent,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="季度财报 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 季度财报分析")
st.caption("跟踪 EPS 超预期与不及预期、整体趋势与财报质量")

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
                value=st.session_state.get("selected_symbol", "AAPL"),
                placeholder="例如：AAPL",
                key="earnings_symbol",
            )
            .upper()
            .strip()
        )
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze = st.button("分析财报", use_container_width=True)

    if not symbol:
        st.info("请输入股票代码以分析其财报。")
        st.stop()

    if analyze or symbol:
        with st.spinner(f"正在分析 {symbol} 的财报……"):
            result = analyze_earnings(symbol)

        if "error" in result:
            st.error(f"错误：{result['error']}")
            st.stop()

        # ─── 抬头 ─────────────────────────────────────────
        name = result.get("name", symbol)
        next_earnings = result.get("next_earnings", {})

        header_parts = [f"**{name}** ({symbol})"]
        if next_earnings and next_earnings.get("date"):
            days = next_earnings.get("days_until")
            date_str = format_date(next_earnings.get("date"))
            if days is not None:
                header_parts.append(f"下一次财报：**{date_str}**（剩余 {days} 天）")
            else:
                header_parts.append(f"下一次财报：**{date_str}**")

        st.markdown(" · ".join(header_parts))

        st.markdown("---")

        # ─── KPI 行 ────────────────────────────────────────
        surprise_hist = result.get("earnings_surprise_history", {}).get("last_8_quarters", {})
        quality = result.get("earnings_quality", {})

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("超预期胜率", surprise_hist.get("beat_rate", "N/A"))
        c2.metric("平均超预期幅度", surprise_hist.get("average_surprise", "N/A"))
        c3.metric("财报质量评分", f"{quality.get('score', 0):.1f}/10")
        pattern = surprise_hist.get("pattern", "N/A")
        pattern_cn = (
            "持续超预期" if "consistent beat" in str(pattern).lower()
            else "波动较大" if "volatile" in str(pattern).lower() or "mixed" in str(pattern).lower()
            else "持续不及预期" if "miss" in str(pattern).lower()
            else pattern
        )
        c4.metric("规律", pattern_cn)

        st.markdown("---")

        # ─── 最近 4 个季度表 ──────────────────────────
        st.markdown("### 季度业绩明细")

        quarters = result.get("last_4_quarters", [])
        if quarters:
            rows = []
            q_labels = []
            surprises = []
            verdicts = []

            for q in quarters:
                verdict = q.get("verdict", "N/A")
                verdict_cn = (
                    "超预期" if "beat" in str(verdict).lower()
                    else "不及预期" if "miss" in str(verdict).lower()
                    else "符合预期" if "meet" in str(verdict).lower() or "inline" in str(verdict).lower()
                    else verdict
                )
                surprise = q.get("eps_surprise_pct", 0) or 0
                q_label = q.get("quarter", "")

                rows.append(
                    {
                        "季度": q_label,
                        "发布日期": format_date(q.get("date")),
                        "营业收入": format_large_number(q.get("revenue_actual")),
                        "净利润": format_large_number(q.get("net_income")),
                        "EPS 实际": (
                            format_currency(q.get("eps_actual"), 2) if q.get("eps_actual") else "--"
                        ),
                        "EPS 预期": (
                            format_currency(q.get("eps_estimate"), 2)
                            if q.get("eps_estimate")
                            else "--"
                        ),
                        "超预期幅度 %": format_percent(surprise),
                        "结果": verdict_cn,
                    }
                )

                q_labels.append(q_label)
                surprises.append(float(surprise) if isinstance(surprise, (int, float)) else 0)
                verdicts.append(verdict)

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # EPS 超预期图
            if q_labels and surprises:
                fig = create_earnings_surprise_chart(q_labels, surprises, verdicts, height=280)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ─── 季度趋势 ────────────────────────────────
        st.markdown("### 季度趋势")

        trends = result.get("quarterly_trends", {})

        def trend_cn(t: str) -> str:
            tl = str(t).lower()
            if "rising" in tl or "improving" in tl or "up" in tl or "growth" in tl:
                return "上行"
            if "falling" in tl or "declining" in tl or "down" in tl or "drop" in tl:
                return "下行"
            if "stable" in tl or "flat" in tl:
                return "平稳"
            if "expand" in tl:
                return "扩张"
            if "contract" in tl:
                return "收缩"
            return str(t)

        c1, c2, c3 = st.columns(3)
        c1.metric("营收趋势", trend_cn(trends.get("revenue_trend", "N/A")))
        c2.metric("利润趋势", trend_cn(trends.get("income_trend", "N/A")))
        c3.metric("利润率轨迹", trend_cn(trends.get("margin_trajectory", "N/A")))

        # 营收 QoQ
        rev_qoq = trends.get("revenue_qoq_growth", [])
        if rev_qoq:
            st.markdown("**营收环比增长**")
            for i, val in enumerate(rev_qoq):
                color = (
                    "#10b981" if "+" in str(val) else "#ef4444" if "-" in str(val) else "#9ca3af"
                )
                st.markdown(
                    f"第 {i+1} 季度：<span style='color:{color}; font-family: JetBrains Mono;'>{val}</span>",
                    unsafe_allow_html=True,
                )

        # 毛利率按季度
        gm_q = trends.get("gross_margins_by_quarter", [])
        if gm_q:
            st.markdown("**各季度毛利率**")
            for i, val in enumerate(gm_q):
                st.markdown(f"第 {i+1} 季度：`{val}`")

        st.markdown("---")

        # ─── 同比对比 ──────────────────────────────────
        yoy = result.get("yoy_comparison", {})
        if yoy:
            st.markdown("### 同比对比 (YoY)")
            c1, c2, c3 = st.columns(3)
            c1.metric("对比周期", yoy.get("comparison_period", "N/A"))
            c2.metric("营收增长", yoy.get("revenue_growth", "N/A"))
            c3.metric("净利润增长", yoy.get("net_income_growth", "N/A"))

        st.markdown("---")

        # ─── 财报质量 ────────────────────────────────
        st.markdown("### 财报质量")

        c1, c2 = st.columns([1, 2])

        with c1:
            score = quality.get("score", 0)
            fig = create_gauge_chart(
                value=round(score, 1),
                title="质量评分",
                min_val=0,
                max_val=10,
                ranges=[
                    {"range": [0, 3], "color": "rgba(239, 68, 68, 0.3)"},
                    {"range": [3, 5], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [5, 7], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [7, 10], "color": "rgba(16, 185, 129, 0.3)"},
                ],
                suffix="/10",
                height=230,
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            assessment = quality.get("assessment", "")
            if assessment:
                assess_l = assessment.lower()
                assess_cn = (
                    "高质量" if "high" in assess_l
                    else "低质量" if "low" in assess_l
                    else assessment
                )
                badge = (
                    "bullish"
                    if "high" in assessment.lower()
                    else "bearish" if "low" in assessment.lower() else "neutral"
                )
                st.markdown(
                    f'<span class="score-badge {badge}" style="font-size: 1rem;">{assess_cn}</span>',
                    unsafe_allow_html=True,
                )

            factors = quality.get("factors", [])
            if factors:
                st.markdown("**质量因素：**")
                for f in factors:
                    st.markdown(f"- {f}")

        # ─── 下一次财报 ───────────────────────────────────
        if next_earnings and next_earnings.get("date"):
            st.markdown("---")
            st.markdown("### 下一次财报")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("日期", format_date(next_earnings.get("date")))
            c2.metric("距今天数", next_earnings.get("days_until", "N/A"))
            c3.metric(
                "EPS 一致预期",
                (
                    format_currency(next_earnings.get("eps_estimate"), 2)
                    if next_earnings.get("eps_estimate")
                    else "N/A"
                ),
            )
            c4.metric("分析师数量", next_earnings.get("number_of_analysts", "N/A"))

else:
    # ─── 对比模式 ────────────────────────────────
    st.markdown("### 财报画像对比")

    symbols_input = st.text_input(
        "输入股票代码（英文逗号分隔，2-10 个）",
        placeholder="例如：AAPL, MSFT, GOOGL",
        key="earnings_compare_input",
    )

    if symbols_input:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

        if len(symbols) < 2:
            st.warning("至少输入 2 个股票代码才能对比。")
            st.stop()

        with st.spinner("正在对比多家公司的财报画像……"):
            result = compare_earnings(tuple(symbols))

        if "error" in result:
            st.error(f"错误：{result['error']}")
            st.stop()

        comparison = result.get("comparison", [])
        if comparison:
            df = pd.DataFrame(comparison)
            column_cn = {
                "symbol": "代码",
                "name": "名称",
                "beat_rate": "超预期胜率",
                "average_surprise": "平均超预期幅度",
                "pattern": "规律",
                "revenue_trend": "营收趋势",
                "income_trend": "利润趋势",
                "earnings_quality_score": "财报质量得分",
                "next_earnings_date": "下一次财报日期",
            }
            column_order = [
                "symbol",
                "name",
                "beat_rate",
                "average_surprise",
                "pattern",
                "revenue_trend",
                "income_trend",
                "earnings_quality_score",
                "next_earnings_date",
            ]
            existing_cols = [c for c in column_order if c in df.columns]
            df = df[existing_cols]

            if "earnings_quality_score" in df.columns:
                df = df.sort_values("earnings_quality_score", ascending=False)

            df_cn = df.rename(columns=column_cn)
            st.dataframe(df_cn, use_container_width=True, hide_index=True)

            # 质量得分排名
            labels = [c.get("symbol", "?") for c in comparison]
            scores = [c.get("earnings_quality_score", 0) or 0 for c in comparison]
            sorted_pairs = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
            if sorted_pairs:
                labels, scores = zip(*sorted_pairs)
                colors = [
                    (
                        "#10b981"
                        if s >= 7
                        else "#3b82f6" if s >= 5 else "#f59e0b" if s >= 3 else "#ef4444"
                    )
                    for s in scores
                ]

                fig = create_horizontal_bar(
                    list(labels),
                    list(scores),
                    title="财报质量得分排名",
                    colors=list(colors),
                )
                st.plotly_chart(fig, use_container_width=True)

            best = result.get("best_earnings_quality")
            if best:
                st.success(f"财报质量最高的公司：**{best}**")
    else:
        st.info("请在上方输入以英文逗号分隔的股票代码以进行财报画像对比。")
