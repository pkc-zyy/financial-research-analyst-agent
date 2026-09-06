"""
历史业绩追踪 - 多周期收益率、基准对比、风险调整指标、
滚动收益率与回撤分析。
"""

import streamlit as st
from components.header import render_header
from components.plotly_charts import (
    create_area_chart,
    create_benchmark_bar,
    create_gauge_chart,
    create_horizontal_bar,
    create_line_chart,
)

from utils.data_service import track_performance
from utils.formatters import format_currency, format_number, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="业绩追踪 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 历史业绩追踪")
st.caption("多周期收益率、基准对比、风险调整指标与回撤分析")

# ─── 股票输入 ────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    symbol = (
        st.text_input(
            "股票代码",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="请输入代码（如 AAPL）",
            key="perf_symbol",
        )
        .strip()
        .upper()
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("分析业绩", use_container_width=True, type="primary")

if analyze_btn and symbol:
    st.session_state.perf_symbol_active = symbol

active = st.session_state.get("perf_symbol_active", "")
if not active:
    st.info("请输入股票代码并点击 **分析业绩** 开始。")
    st.stop()

# ─── 获取数据 ──────────────────────────────────────────────
result = track_performance(active)

if "error" in result:
    st.error(f"错误：{result['error']}")
    st.stop()

# ─── 头部信息 ──────────────────────────────────────────────────
sector = result.get("sector", "")
sector_etf = result.get("sector_etf", "")
current_price = result.get("current_price", 0)
date_range = f"{result.get('start_date', '')} 至 {result.get('end_date', '')}"

st.markdown(
    f"""
<div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem;
            background: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};
            margin-bottom: 1.5rem;">
    <div>
        <span style="font-size: 1.5rem; font-weight: 700; color: {COLORS['text_primary']}; font-family: 'Inter', sans-serif;">
            {active}
        </span>
        <span style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin-left: 0.75rem;">
            {sector}{f' · {sector_etf}' if sector_etf else ''}
        </span>
    </div>
    <div style="margin-left: auto; text-align: right;">
        <span style="font-size: 1.25rem; font-weight: 600; color: {COLORS['text_primary']}; font-family: 'JetBrains Mono', monospace;">
            {format_currency(current_price)}
        </span>
        <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{date_range} · {result.get('data_points', 0)} 个数据点</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 绝对收益率 ───────────────────────────────────────
abs_returns = result.get("absolute_returns", {})

st.markdown(
    f"""
<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
    <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
    <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
        多周期收益率
    </h3>
    <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
</div>
""",
    unsafe_allow_html=True,
)

horizon_display = [
    ("1日", "1_day"),
    ("1周", "1_week"),
    ("1月", "1_month"),
    ("3月", "3_month"),
    ("6月", "6_month"),
    ("年初至今", "ytd"),
    ("1年", "1_year"),
    ("3年", "3_year"),
    ("5年", "5_year"),
]

cols = st.columns(len(horizon_display))
for col, (label, key) in zip(cols, horizon_display):
    val = abs_returns.get(key)
    with col:
        if val is not None:
            delta_color = "normal" if val >= 0 else "inverse"
            col.metric(
                label=label,
                value=format_percent(val),
                delta=format_percent(val),
                delta_color=delta_color,
            )
        else:
            col.metric(label=label, value="--")

st.markdown("<br>", unsafe_allow_html=True)

# ─── 基准对比 ───────────────────────────────────
bench = result.get("benchmark_comparison", {})

if bench:
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            基准对比
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    bench_tabs = list(bench.keys())
    bench_tab_labels = []
    for bt in bench_tabs:
        entry = bench[bt]
        bench_tab_labels.append(entry.get("benchmark", bt))

    tabs = st.tabs(bench_tab_labels)

    for tab, bt in zip(tabs, bench_tabs):
        entry = bench[bt]
        with tab:
            # 评估
            assessment = entry.get("assessment", "")
            if "Outperforming" in assessment:
                assessment_color = COLORS["success"]
            elif "Underperforming" in assessment:
                assessment_color = COLORS["danger"]
            else:
                assessment_color = COLORS["text_muted"]

            def _assess_cn(a):
                if "Outperforming" in a:
                    return a.replace("Outperforming", "跑赢")
                if "Underperforming" in a:
                    return a.replace("Underperforming", "跑输")
                return a or "表现持平基准"

            st.markdown(
                f"""
            <div style="font-size: 0.9rem; color: {assessment_color}; font-weight: 600;
                        font-family: 'Inter', sans-serif; margin-bottom: 1rem;">
                {_assess_cn(assessment)}
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Alpha 指标
            alpha_horizons = ["1_month", "3_month", "1_year", "3_year"]
            alpha_labels = ["1月", "3月", "1年", "3年"]
            stock_vals = []
            bench_vals = []
            valid_labels = []

            for al, ah in zip(alpha_labels, alpha_horizons):
                s = entry.get(f"{ah}_stock")
                b = entry.get(f"{ah}_benchmark")
                if s is not None and b is not None:
                    stock_vals.append(s)
                    bench_vals.append(b)
                    valid_labels.append(al)

            if stock_vals:
                fig = create_benchmark_bar(
                    valid_labels,
                    stock_vals,
                    bench_vals,
                    stock_label=active,
                    benchmark_label=entry.get("benchmark", "基准"),
                    title=f"{active} 对比 {entry.get('benchmark', '基准')} 收益率",
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)

            # Alpha 汇总行
            alpha_cols = st.columns(len(alpha_horizons))
            for col, al, ah in zip(alpha_cols, alpha_labels, alpha_horizons):
                alpha = entry.get(f"{ah}_alpha")
                if alpha is not None:
                    col.metric(
                        label=f"{al} 超额收益(Alpha)",
                        value=format_percent(alpha),
                        delta=format_percent(alpha),
                        delta_color="normal" if alpha >= 0 else "inverse",
                    )

    st.markdown("<br>", unsafe_allow_html=True)

# ─── 风险调整指标 ──────────────────────────────────
risk = result.get("risk_adjusted_metrics", {})

if risk:
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            风险调整指标
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        sharpe = risk.get("sharpe_ratio", 0)
        sharpe_rating = risk.get("sharpe_rating", "")
        fig = create_gauge_chart(
            value=max(-1, min(sharpe, 4)),
            title="夏普比率 (Sharpe)",
            min_val=-1,
            max_val=4,
            ranges=[
                {"range": [-1, 0.5], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [0.5, 1.0], "color": "rgba(245, 158, 11, 0.3)"},
                {"range": [1.0, 2.0], "color": "rgba(59, 130, 246, 0.3)"},
                {"range": [2.0, 4.0], "color": "rgba(16, 185, 129, 0.3)"},
            ],
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"评级：**{sharpe_rating}**")

    with r2:
        sortino = risk.get("sortino_ratio", 0)
        sortino_rating = risk.get("sortino_rating", "")
        fig = create_gauge_chart(
            value=max(-1, min(sortino, 4)),
            title="索提诺比率 (Sortino)",
            min_val=-1,
            max_val=4,
            ranges=[
                {"range": [-1, 0.5], "color": "rgba(239, 68, 68, 0.3)"},
                {"range": [0.5, 1.0], "color": "rgba(245, 158, 11, 0.3)"},
                {"range": [1.0, 2.0], "color": "rgba(59, 130, 246, 0.3)"},
                {"range": [2.0, 4.0], "color": "rgba(16, 185, 129, 0.3)"},
            ],
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"评级：**{sortino_rating}**")

    with r3:
        beta = risk.get("beta")
        if beta is not None:
            beta_interp = risk.get("beta_interpretation", "")
            # Beta 说明简单汉化：低波动/接近市场/高波动
            def _beta_cn(txt):
                t = (txt or "").lower()
                if "less volatile" in t or "low volatility" in t or "defensive" in t:
                    return "防御性：波动低于大盘"
                if "more volatile" in t or "high volatility" in t or "aggressive" in t:
                    return "激进型：波动高于大盘"
                if "market-like" in t or "average" in t or "similar" in t:
                    return "中性：波动与大盘相近"
                return txt or "--"

            fig = create_gauge_chart(
                value=max(0, min(beta, 3)),
                title="贝塔系数 (Beta)",
                min_val=0,
                max_val=3,
                ranges=[
                    {"range": [0, 0.8], "color": "rgba(16, 185, 129, 0.3)"},
                    {"range": [0.8, 1.2], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [1.2, 2.0], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [2.0, 3.0], "color": "rgba(239, 68, 68, 0.3)"},
                ],
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(_beta_cn(beta_interp))
        else:
            st.metric("贝塔系数", "--")

    with r4:
        vol = risk.get("annual_volatility", 0)
        st.metric("年化波动率", format_percent(vol, include_sign=False))
        st.metric(
            "日波动率", format_percent(risk.get("daily_volatility", 0), include_sign=False)
        )

    st.markdown("<br>", unsafe_allow_html=True)

# ─── 滚动收益率 ────────────────────────────────────────
rolling = result.get("rolling_returns", {})

if rolling.get("values"):
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            30日滚动收益率
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 汇总指标
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    rc1.metric("当前值", format_percent(rolling.get("current")))
    rc2.metric("均值", format_percent(rolling.get("average")))
    rc3.metric("最佳", format_percent(rolling.get("max")))
    rc4.metric("最差", format_percent(rolling.get("min")))
    trend = rolling.get("trend", "") or "稳定"
    trend_cn = (
        trend
        .replace("negative", "偏弱")
        .replace("weakening", "走弱")
        .replace("positive", "偏强")
        .replace("strengthening", "走强")
        .replace("stable", "稳定")
        .replace("Stable", "稳定")
    )
    trend_color = "normal"
    if "偏弱" in trend_cn or "走弱" in trend_cn:
        trend_color = "off"
    rc5.metric("趋势", trend_cn)

    # 滚动收益率图表
    fig = create_line_chart(
        dates=rolling.get("dates", []),
        values=rolling.get("values", []),
        title="30日滚动收益率 (%)",
        fill=True,
        height=300,
        show_zero_line=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── 回撤分析 ──────────────────────────────────────
dd = result.get("drawdown_analysis", {})

if dd.get("drawdown_series"):
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            回撤分析 (近1年)
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    dc1, dc2, dc3, dc4 = st.columns(4)
    dc1.metric("最大回撤", format_percent(dd.get("max_drawdown")))
    dc2.metric("最大回撤日期", dd.get("max_drawdown_date", "--"))
    recovery = dd.get("recovery_days")
    dc3.metric("修复天数", f"{recovery} 天" if recovery else "尚未修复")
    dc4.metric("当前回撤", format_percent(dd.get("current_drawdown")))

    fig = create_area_chart(
        dates=dd.get("dates", []),
        values=dd.get("drawdown_series", []),
        title="距历史高点回撤 (%)",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── 收益统计 ──────────────────────────────────────
stats = result.get("return_statistics", {})

if stats:
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            日收益率统计 (近1年)
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    sc1.metric("日均收益率", format_percent(stats.get("mean_daily"), decimals=3))
    sc2.metric("日收益中位数", format_percent(stats.get("median_daily"), decimals=3))
    sc3.metric("最佳单日", format_percent(stats.get("best_day")))
    sc4.metric("最差单日", format_percent(stats.get("worst_day")))
    sc5.metric("上涨天数占比", format_percent(stats.get("positive_days_pct"), include_sign=False))
    sc6.metric("标准差", format_percent(stats.get("std_daily"), decimals=3, include_sign=False))

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"""
<div style="text-align: center; padding: 1rem; border-top: 1px solid {COLORS['border']};">
    <p style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: {COLORS['text_muted']};">
        业绩数据来源：Yahoo Finance · 收益率为价格口径（不含分红再投资）· 过往业绩不代表未来表现
    </p>
</div>
""",
    unsafe_allow_html=True,
)
