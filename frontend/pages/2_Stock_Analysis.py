"""
个股分析 - 综合技术面、基本面、舆情与风险分析。
"""

import numpy as np
import pandas as pd
import streamlit as st
from components.charts import render_candlestick_chart
from components.data_tables import render_metrics_table, render_styled_dataframe
from components.header import render_header
from components.metrics_cards import (
    render_company_header,
    render_news_card,
    render_score_badge,
)
from components.plotly_charts import (
    create_donut_chart,
    create_gauge_chart,
    create_grouped_bar,
    create_radar_chart,
)

from utils.data_service import (
    analyze_news_sentiment,
    get_company_info,
    get_company_news,
    get_financial_health,
    get_financial_statements,
    get_historical_data,
    get_profitability_ratios,
    get_stock_price,
    get_technical_analysis,
    get_valuation_ratios,
)
from utils.formatters import (
    format_currency,
    format_date,
    format_large_number,
    format_number,
    format_percent,
    format_ratio,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="个股分析 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 个股分析")

# ─── 代码输入 ────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    symbol = (
        st.text_input(
            "股票代码",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="例如：AAPL",
            key="stock_analysis_symbol",
        )
        .upper()
        .strip()
    )

with col2:
    period_map = {
        "1 周": "5d",
        "1 月": "1mo",
        "3 月": "3mo",
        "6 月": "6mo",
        "1 年": "1y",
        "5 年": "5y",
    }
    period_label = st.selectbox("周期", list(period_map.keys()), index=4, key="stock_period")
    period = period_map[period_label]

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_clicked = st.button("开始分析", use_container_width=True, key="analyze_btn")

if analyze_clicked:
    st.session_state.selected_symbol = symbol

if not symbol:
    st.info("请在上方输入股票代码以开始分析。")
    st.stop()

# ─── 获取数据 ──────────────────────────────────────────────
with st.spinner(f"正在加载 {symbol} 的数据……"):
    price_data = get_stock_price(symbol)
    company = get_company_info(symbol)

if "error" in price_data:
    st.error(f"未找到 **{symbol}** 的股票数据，请确认股票代码正确。")
    st.stop()

# ─── 公司抬头 ──────────────────────────────────────────
render_company_header(
    symbol=symbol,
    name=company.get("name", symbol),
    price=price_data.get("current_price", 0),
    change_pct=price_data.get("change_percent", 0),
    market_cap=format_large_number(price_data.get("market_cap")),
    sector=company.get("sector", ""),
)

# 关键指标行
key_metrics = [
    {"label": "开盘价", "value": format_currency(price_data.get("open"))},
    {"label": "当日最高", "value": format_currency(price_data.get("day_high"))},
    {"label": "当日最低", "value": format_currency(price_data.get("day_low"))},
    {"label": "52 周最高", "value": format_currency(price_data.get("52_week_high"))},
    {"label": "52 周最低", "value": format_currency(price_data.get("52_week_low"))},
    {
        "label": "成交量",
        "value": f"{price_data.get('volume', 0):,.0f}" if price_data.get("volume") else "--",
    },
]

cols = st.columns(6)
for col, m in zip(cols, key_metrics):
    col.metric(label=m["label"], value=m["value"])

# ─── 价格走势图 ─────────────────────────────────────────────
st.markdown("### 价格走势图")

hist = get_historical_data(symbol, period)
tech = get_technical_analysis(symbol, period)

if "error" not in hist and hist.get("dates"):
    # 构造均线叠加数据
    sma_data = {}
    if "error" not in tech:
        ma = tech.get("moving_averages", {})
        # 工具目前仅返回单个数值，无法提供完整序列；暂时不绘制均线叠加。

    # 支撑 / 阻力位
    sr = tech.get("support_resistance", {}) if "error" not in tech else {}
    support = sr.get("support_levels", [])
    resistance = sr.get("resistance_levels", [])

    render_candlestick_chart(
        dates=hist["dates"],
        opens=hist["opens"],
        highs=hist["highs"],
        lows=hist["lows"],
        closes=hist["closes"],
        volumes=hist.get("volumes"),
        support_levels=support[:3],
        resistance_levels=resistance[:3],
        height=480,
    )
else:
    st.warning("无法加载历史数据以绘制图表。")

# ─── 分析选项卡 ───────────────────────────────────────────
tab_tech, tab_fund, tab_sent, tab_risk = st.tabs(["技术面", "基本面", "舆情情绪", "风险"])

# ═══ 技术面 Tab ═══════════════════════════════════════════
with tab_tech:
    if "error" in tech:
        st.warning("技术分析暂时不可用。")
    else:
        # RSI、MACD、均线趋势行
        c1, c2, c3 = st.columns(3)

        # RSI 仪表盘
        with c1:
            rsi = tech.get("rsi", {})
            rsi_val = rsi.get("value", 50)
            if isinstance(rsi_val, (int, float)):
                fig = create_gauge_chart(
                    value=round(rsi_val, 1),
                    title="RSI (14)",
                    min_val=0,
                    max_val=100,
                    ranges=[
                        {"range": [0, 30], "color": "rgba(16, 185, 129, 0.3)"},
                        {"range": [30, 70], "color": "rgba(245, 158, 11, 0.15)"},
                        {"range": [70, 100], "color": "rgba(239, 68, 68, 0.3)"},
                    ],
                    height=220,
                )
                st.plotly_chart(fig, use_container_width=True)
                signal = rsi.get("signal", "NEUTRAL")
                sig_cn = (
                    "超卖"
                    if "OVERSOLD" in str(signal).upper()
                    else "超买" if "OVERBOUGHT" in str(signal).upper() else "中性"
                )
                badge = (
                    "bullish"
                    if "OVERSOLD" in str(signal).upper()
                    else "bearish" if "OVERBOUGHT" in str(signal).upper() else "neutral"
                )
                st.markdown(
                    f'<div style="text-align:center;"><span class="score-badge {badge}">{sig_cn}</span></div>',
                    unsafe_allow_html=True,
                )

        # MACD
        with c2:
            macd = tech.get("macd", {})
            st.markdown("#### MACD")
            crossover = str(macd.get("crossover", "--")).lower()
            trend = str(macd.get("trend", "--")).lower()
            crossover_cn = (
                "金叉" if "bullish" in crossover or crossover == "golden"
                else "死叉" if "bearish" in crossover or crossover == "death"
                else str(macd.get("crossover", "--")).title()
            )
            trend_cn = (
                "看涨" if "bull" in trend
                else "看跌" if "bear" in trend
                else "中性" if trend != "--" else "--"
            )
            macd_metrics = {
                "MACD 线": format_number(macd.get("macd_line"), 4),
                "信号线": format_number(macd.get("signal_line"), 4),
                "柱状图": format_number(macd.get("histogram"), 4),
                "交叉": crossover_cn,
                "趋势": trend_cn,
            }
            for label, val in macd_metrics.items():
                st.markdown(f"**{label}:** `{val}`")

            badge = (
                "bullish"
                if "bull" in trend
                else "bearish" if "bear" in trend else "neutral"
            )
            st.markdown(
                f'<div style="text-align:center; margin-top: 0.5rem;"><span class="score-badge {badge}">{trend_cn.upper()}</span></div>',
                unsafe_allow_html=True,
            )

        # 移动均线
        with c3:
            ma = tech.get("moving_averages", {})
            st.markdown("#### 移动均线")
            current = ma.get("current_price", price_data.get("current_price", 0))
            ma_items = [
                ("SMA 20", ma.get("sma_20")),
                ("EMA 20", ma.get("ema_20")),
                ("SMA 50", ma.get("sma_50")),
                ("EMA 50", ma.get("ema_50")),
                ("SMA 200", ma.get("sma_200")),
                ("EMA 200", ma.get("ema_200")),
            ]
            for label, val in ma_items:
                if val is not None:
                    color = "#10b981" if current > val else "#ef4444"
                    pos = "上方" if current > val else "下方"
                    st.markdown(
                        f"**{label}:** `{format_currency(val)}` <span style='color:{color}; font-size:0.8rem;'>({pos})</span>",
                        unsafe_allow_html=True,
                    )

            trend = ma.get("trend", "neutral")
            badge = (
                "bullish"
                if "bullish" in str(trend).lower()
                else "bearish" if "bearish" in str(trend).lower() else "neutral"
            )
            trend_cn = (
                "看涨" if "bullish" in str(trend).lower()
                else "看跌" if "bearish" in str(trend).lower() else "中性"
            )
            st.markdown(
                f'<div style="text-align:center; margin-top: 0.5rem;"><span class="score-badge {badge}">{trend_cn.upper()} 趋势</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # 布林带 & 形态识别
        c1, c2 = st.columns(2)

        with c1:
            bb = tech.get("bollinger_bands", {})
            if bb and "error" not in bb:
                st.markdown("#### 布林带")
                position = str(bb.get("position", "--")).replace("_", " ").lower()
                pos_cn = (
                    "上轨之上" if "above upper" in position
                    else "下轨之下" if "below lower" in position
                    else "中轨附近" if "middle" in position
                    else str(bb.get("position", "--")).replace("_", " ").title()
                )
                bb_items = {
                    "上轨": format_currency(bb.get("upper_band")),
                    "中轨": format_currency(bb.get("middle_band")),
                    "下轨": format_currency(bb.get("lower_band")),
                    "带宽": format_number(bb.get("bandwidth"), 4),
                    "%B 指标": format_number(bb.get("percent_b"), 4),
                    "位置": pos_cn,
                }
                for label, val in bb_items.items():
                    st.markdown(f"**{label}:** `{val}`")

        with c2:
            patterns = tech.get("patterns", {})
            detected = patterns.get("patterns_detected", [])
            st.markdown("#### K 线形态识别")
            if detected:
                for p in detected:
                    conf = p.get("confidence", 0)
                    impl = p.get("implication", "neutral")
                    impl_cn = (
                        "看涨" if "bullish" in str(impl).lower()
                        else "看跌" if "bearish" in str(impl).lower() else "中性"
                    )
                    badge = (
                        "bullish"
                        if "bullish" in str(impl).lower()
                        else "bearish" if "bearish" in str(impl).lower() else "neutral"
                    )
                    st.markdown(
                        f'<span class="score-badge {badge}">{p.get("name", "未知形态")} '
                        f"({conf*100:.0f}% 置信度 · {impl_cn})</span>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("当前周期未检测到显著形态。")

        # 支撑与阻力
        sr = tech.get("support_resistance", {})
        if sr and "error" not in sr:
            st.markdown("---")
            st.markdown("#### 支撑位 & 阻力位")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**支撑位**")
                for level in sr.get("support_levels", [])[:5]:
                    st.markdown(
                        f"<span style='color: #10b981; font-family: JetBrains Mono;'>{format_currency(level)}</span>",
                        unsafe_allow_html=True,
                    )
            with c2:
                st.markdown("**阻力位**")
                for level in sr.get("resistance_levels", [])[:5]:
                    st.markdown(
                        f"<span style='color: #ef4444; font-family: JetBrains Mono;'>{format_currency(level)}</span>",
                        unsafe_allow_html=True,
                    )

# ═══ 基本面 Tab ═════════════════════════════════════════════
with tab_fund:
    with st.spinner("正在加载基本面数据……"):
        financials = get_financial_statements(symbol)
        health = get_financial_health(symbol)
        valuation = get_valuation_ratios(symbol)
        profitability = get_profitability_ratios(symbol)

    # 估值指标行
    if "error" not in valuation:
        st.markdown("#### 估值")
        val_metrics = [
            {"label": "市盈率 (P/E)", "value": format_number(valuation.get("pe_ratio"))},
            {"label": "市净率 (P/B)", "value": format_number(valuation.get("pb_ratio"))},
            {"label": "市销率 (P/S)", "value": format_number(valuation.get("ps_ratio"))},
            {"label": "EV/EBITDA", "value": format_number(valuation.get("ev_ebitda"))},
        ]
        cols = st.columns(4)
        for col, m in zip(cols, val_metrics):
            col.metric(label=m["label"], value=m["value"])

        # 估值评价
        assessments = []
        for key in ["pe_assessment", "pb_assessment", "ev_ebitda_assessment"]:
            a = valuation.get(key)
            if a:
                assessments.append(a)
        if assessments:
            st.caption("估值评价：" + " | ".join(assessments))

    st.markdown("---")

    # 财务健康 & 盈利能力
    c1, c2 = st.columns(2)

    with c1:
        if "error" not in health:
            health_score = health.get("health_score", 0)
            fig = create_gauge_chart(
                value=round(health_score, 1),
                title="财务健康评分",
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
            assessment = health.get("overall_assessment", "")
            if assessment:
                assess_cn = (
                    "强劲" if "strong" in assessment.lower()
                    else "偏弱" if "weak" in assessment.lower() else "稳健"
                )
                badge = (
                    "bullish"
                    if "strong" in assessment.lower()
                    else "bearish" if "weak" in assessment.lower() else "neutral"
                )
                st.markdown(
                    f'<div style="text-align:center;"><span class="score-badge {badge}">{assess_cn}</span></div>',
                    unsafe_allow_html=True,
                )

            # 优势 / 劣势
            strengths = health.get("strengths", [])
            weaknesses = health.get("weaknesses", [])
            if strengths:
                st.markdown("**核心优势**")
                for s in strengths[:5]:
                    st.markdown(f'<div class="strength-item">{s}</div>', unsafe_allow_html=True)
            if weaknesses:
                st.markdown("**风险因素**")
                for w in weaknesses[:5]:
                    st.markdown(f'<div class="weakness-item">{w}</div>', unsafe_allow_html=True)
        else:
            st.caption("财务健康数据不可用。")

    with c2:
        if "error" not in profitability:
            # 雷达图
            categories = ["毛利率", "经营利润率", "净利率", "股本回报率 ROE", "资产回报率 ROA"]
            raw_vals = [
                profitability.get("gross_margin"),
                profitability.get("operating_margin"),
                profitability.get("net_margin"),
                profitability.get("roe"),
                profitability.get("roa"),
            ]
            values = [
                round(v * 100, 1) if v and abs(v) < 1 else round(v, 1) if v else 0 for v in raw_vals
            ]

            fig = create_radar_chart(categories, values, title="盈利能力画像", height=320)
            st.plotly_chart(fig, use_container_width=True)

            # ROE 评价
            roe_assessment = profitability.get("roe_assessment", "")
            if roe_assessment:
                st.caption(f"ROE 评价：{roe_assessment}")
        else:
            st.caption("盈利能力数据不可用。")

    # 财务报表
    st.markdown("---")
    st.markdown("#### 财务报表")

    if "error" not in financials:
        fs_tabs = st.tabs(["利润表", "资产负债表", "现金流量表"])

        with fs_tabs[0]:
            income = financials.get("income_statement")
            if income:
                render_metrics_table(
                    {
                        "营业收入": format_large_number(income.get("total_revenue")),
                        "毛利润": format_large_number(income.get("gross_profit")),
                        "经营利润": format_large_number(income.get("operating_income")),
                        "净利润": format_large_number(income.get("net_income")),
                        "EBITDA": format_large_number(income.get("ebitda")),
                    }
                )
            else:
                st.caption("利润表数据不可用。")

        with fs_tabs[1]:
            balance = financials.get("balance_sheet")
            if balance:
                render_metrics_table(
                    {
                        "总资产": format_large_number(balance.get("total_assets")),
                        "总负债": format_large_number(balance.get("total_liabilities")),
                        "股东权益合计": format_large_number(balance.get("total_equity")),
                        "现金及等价物": format_large_number(balance.get("cash")),
                        "总债务": format_large_number(balance.get("total_debt")),
                    }
                )
            else:
                st.caption("资产负债表数据不可用。")

        with fs_tabs[2]:
            cashflow = financials.get("cash_flow")
            if cashflow:
                render_metrics_table(
                    {
                        "经营活动现金流": format_large_number(
                            cashflow.get("operating_cash_flow")
                        ),
                        "资本支出": format_large_number(
                            cashflow.get("capital_expenditure")
                        ),
                        "自由现金流": format_large_number(cashflow.get("free_cash_flow")),
                    }
                )
            else:
                st.caption("现金流量表数据不可用。")
    else:
        st.caption("财务报表数据不可用。")

# ═══ 舆情情绪 Tab ═══════════════════════════════════════════
with tab_sent:
    st.markdown("#### 新闻舆情情绪")

    sent_data = analyze_news_sentiment(symbol)
    if "error" not in sent_data and sent_data.get("articles_analyzed", 0) > 0:
        agg_sent = sent_data.get("aggregate_sentiment", {})
        sent_dist = sent_data.get("distribution", {})

        # 舆情概览行
        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc1:
            agg_score = agg_sent.get("score", 0)
            gauge_val = (agg_score + 1) / 2 * 100
            fig = create_gauge_chart(
                value=round(gauge_val, 1),
                title="舆情分数",
                min_val=0,
                max_val=100,
                ranges=[
                    {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
                    {"range": [30, 45], "color": "rgba(245, 158, 11, 0.3)"},
                    {"range": [45, 55], "color": "rgba(161, 161, 170, 0.2)"},
                    {"range": [55, 70], "color": "rgba(59, 130, 246, 0.3)"},
                    {"range": [70, 100], "color": "rgba(16, 185, 129, 0.3)"},
                ],
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)
            label_cn_map = {"positive": "正面", "negative": "负面", "neutral": "中性"}
            label_en = (agg_sent.get("label", "Neutral") or "Neutral").lower()
            label_cn = label_cn_map.get(label_en, "中性")
            st.caption(
                f"**{label_cn}** · 共分析 {sent_data.get('articles_analyzed', 0)} 篇文章"
            )

        with sc2:
            if sent_dist:
                fig = create_donut_chart(
                    labels=["正面", "中性", "负面"],
                    values=[
                        sent_dist.get("positive", 0),
                        sent_dist.get("neutral", 0),
                        sent_dist.get("negative", 0),
                    ],
                    title="分布",
                    colors=["#22c55e", "#71717a", "#ef4444"],
                    height=200,
                )
                st.plotly_chart(fig, use_container_width=True)

        with sc3:
            vol = sent_data.get("volume", {})
            st.metric("24 小时文章数", vol.get("last_24h", 0))
            st.metric("7 天文章数", vol.get("last_7d", 0))
            trend_dir = sent_data.get("sentiment_trend", {}).get("direction", "Stable")
            trend_cn = (
                "向好" if "rising" in str(trend_dir).lower() or "up" in str(trend_dir).lower()
                else "向差" if "falling" in str(trend_dir).lower() or "down" in str(trend_dir).lower()
                else "稳定"
            )
            st.metric("趋势", trend_cn)

        # 已打分文章
        scored = sent_data.get("scored_articles", [])
        if scored:
            st.markdown("##### 文章打分")
            cols = st.columns(2)
            for i, article in enumerate(scored[:8]):
                sent = article.get("sentiment", {})
                score = sent.get("score", 0)
                label = sent.get("label", "Neutral")
                label_cn = label_cn_map.get((label or "").lower(), "中性")
                with cols[i % 2]:
                    render_news_card(
                        title=f"[{score:+.2f}] {article.get('title', '未命名文章')}",
                        source=f"{article.get('source', '')} · {label_cn}",
                        date=format_date(article.get("published_at", "")),
                        description=article.get("description", ""),
                        url=article.get("url", ""),
                        thumbnail=article.get("thumbnail", ""),
                        content_type=article.get("type", ""),
                    )
    else:
        news = get_company_news(symbol)
        if news:
            cols = st.columns(2)
            for i, article in enumerate(news[:8]):
                with cols[i % 2]:
                    render_news_card(
                        title=article.get("title", "未命名文章"),
                        source=article.get("source", ""),
                        date=format_date(article.get("published_at", "")),
                        description=article.get("description", ""),
                        url=article.get("url", ""),
                        thumbnail=article.get("thumbnail", ""),
                        content_type=article.get("type", ""),
                    )
        else:
            st.info(f"暂未找到 {symbol} 的近期新闻。")

# ═══ 风险 Tab ════════════════════════════════════════════════
with tab_risk:
    st.markdown("#### 风险指标")

    if "error" not in hist and hist.get("closes"):
        closes = np.array(hist["closes"], dtype=float)
        returns = np.diff(closes) / closes[:-1]

        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        max_dd = 0.0
        peak = closes[0]
        for p in closes:
            if p > peak:
                peak = p
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd

        # 52 周区间
        high_52 = price_data.get("52_week_high", max(closes))
        low_52 = price_data.get("52_week_low", min(closes))
        current = price_data.get("current_price", closes[-1])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("日波动率", format_percent(daily_vol * 100))
        c2.metric("年化波动率", format_percent(annual_vol * 100))
        c3.metric("最大回撤", format_percent(-max_dd * 100))

        # 夏普比率（假设无风险利率 ~5%）
        avg_return = np.mean(returns) * 252
        sharpe = (avg_return - 0.05) / annual_vol if annual_vol > 0 else 0
        c4.metric("夏普比率", format_number(sharpe))

        st.markdown("---")

        # 52 周区间可视化
        st.markdown("#### 52 周区间")
        if high_52 > low_52:
            pct_pos = ((current - low_52) / (high_52 - low_52)) * 100
            pct_pos = max(0, min(100, pct_pos))
        else:
            pct_pos = 50

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 1rem; margin: 1rem 0;">
                <span style="font-family: JetBrains Mono; color: #ef4444; font-size: 0.85rem;">
                    {format_currency(low_52)}
                </span>
                <div style="flex: 1; height: 8px; background: linear-gradient(to right, #ef4444, #f59e0b, #10b981);
                            border-radius: 999px; position: relative;">
                    <div style="position: absolute; top: -8px; left: {pct_pos}%;
                                width: 12px; height: 24px; background: white; border-radius: 6px;
                                transform: translateX(-50%); box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    </div>
                </div>
                <span style="font-family: JetBrains Mono; color: #10b981; font-size: 0.85rem;">
                    {format_currency(high_52)}
                </span>
            </div>
            <div style="text-align: center; color: #9ca3af; font-size: 0.8rem;">
                当前价：{format_currency(current)}（区间位置 {pct_pos:.0f}%）
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 收益率分布
        st.markdown("---")
        st.markdown("#### 收益率统计")
        stats = {
            "日均收益率": format_percent(np.mean(returns) * 100, 4),
            "日收益率中位数": format_percent(np.median(returns) * 100, 4),
            "单日最大涨幅": format_percent(np.max(returns) * 100),
            "单日最大跌幅": format_percent(np.min(returns) * 100),
            "上涨天数": f"{(returns > 0).sum()} / {len(returns)} ({(returns > 0).mean() * 100:.1f}%)",
            "偏度": format_number(float(pd.Series(returns).skew()), 4),
            "峰度": format_number(float(pd.Series(returns).kurtosis()), 4),
        }
        render_metrics_table(stats)
    else:
        st.warning("风险分析需要历史数据支持。")
