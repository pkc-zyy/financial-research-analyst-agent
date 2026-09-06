"""
仪表盘 - 市场总览、快捷分析、新闻动态。
"""

import streamlit as st
from components.charts import render_area_chart, render_candlestick_chart
from components.header import render_header
from components.metrics_cards import render_kpi_row, render_news_card

from utils.data_service import (
    get_company_news,
    get_historical_data,
    get_stock_price,
    get_technical_analysis,
)
from utils.formatters import (
    format_currency,
    format_date,
    format_large_number,
    format_percent,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="仪表盘 | 智能金融 AI", page_icon=":chart_with_upwards_trend:", layout="wide"
)
inject_css()
init_session_state()
render_header()

st.markdown("## 仪表盘")
st.caption("市场总览与快捷分析")

# ─── 主要指数 ──────────────────────────────────────────
indices = [
    ("SPY", "标普 500"),
    ("QQQ", "纳斯达克 100"),
    ("DIA", "道琼斯工业"),
    ("IWM", "罗素 2000"),
]

cols = st.columns(4)
for col, (ticker, label) in zip(cols, indices):
    with col:
        data = get_stock_price(ticker)
        if "error" not in data:
            col.metric(
                label=label,
                value=format_currency(data.get("current_price", 0)),
                delta=format_percent(data.get("change_percent", 0)),
            )
        else:
            col.metric(label=label, value="--")

st.markdown("<br>", unsafe_allow_html=True)

# ─── 主布局 ─────────────────────────────────────────────
left_col, right_col = st.columns([3, 2])

# ─── 市场图表 ────────────────────────────────────────────
with left_col:
    st.markdown("### 市场走势图")
    chart_symbol = st.selectbox(
        "指数",
        ["SPY", "QQQ", "DIA", "IWM"],
        label_visibility="collapsed",
        key="dashboard_chart_symbol",
    )
    period = st.radio(
        "周期",
        ["1mo", "3mo", "6mo", "1y"],
        horizontal=True,
        index=3,
        label_visibility="collapsed",
        key="dashboard_chart_period",
        format_func=lambda x: {"1mo": "1 月", "3mo": "3 月", "6mo": "6 月", "1y": "1 年"}[x],
    )

    hist = get_historical_data(chart_symbol, period)
    if "error" not in hist and hist.get("dates"):
        render_candlestick_chart(
            dates=hist["dates"],
            opens=hist["opens"],
            highs=hist["highs"],
            lows=hist["lows"],
            closes=hist["closes"],
            volumes=hist.get("volumes"),
            height=420,
        )
    else:
        st.warning(f"无法加载 {chart_symbol} 的图表数据。")

# ─── 自选股 & 快捷分析 ──────────────────────────────
with right_col:
    st.markdown("### 我的自选股")

    watchlist = st.session_state.get("watchlist", [])
    if watchlist:
        for sym in watchlist:
            data = get_stock_price(sym)
            if "error" not in data:
                price = data.get("current_price", 0)
                change = data.get("change_percent", 0)
                change_color = "#10b981" if change >= 0 else "#ef4444"
                change_sign = "+" if change >= 0 else ""

                c1, c2, c3 = st.columns([1, 1.5, 1])
                c1.markdown(f"**{sym}**")
                c2.markdown(f"`{format_currency(price)}`")
                c3.markdown(
                    f"<span style='color: {change_color}; font-family: JetBrains Mono, monospace; font-size: 0.85rem;'>"
                    f"{change_sign}{change:.2f}%</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("请在左侧边栏将股票代码加入自选股。")

    st.markdown("---")

    # 快捷分析
    st.markdown("### 快捷分析")
    quick_sym = st.text_input(
        "股票代码",
        placeholder="请输入股票代码……",
        key="quick_analysis_input",
        label_visibility="collapsed",
    )

    if quick_sym:
        quick_sym = quick_sym.upper().strip()
        with st.spinner(f"正在分析 {quick_sym}……"):
            price_data = get_stock_price(quick_sym)
            tech = get_technical_analysis(quick_sym)

        if "error" not in price_data:
            st.metric(
                "现价",
                format_currency(price_data.get("current_price", 0)),
                delta=format_percent(price_data.get("change_percent", 0)),
            )

            if "error" not in tech:
                rsi = tech.get("rsi", {})
                macd = tech.get("macd", {})

                c1, c2 = st.columns(2)
                c1.metric(
                    "RSI",
                    (
                        f"{rsi.get('value', '--'):.1f}"
                        if isinstance(rsi.get("value"), (int, float))
                        else "--"
                    ),
                )
                trend = macd.get("trend", "--")
                trend_cn = (
                    "看涨" if trend and "bull" in trend.lower()
                    else "看跌" if trend and "bear" in trend.lower()
                    else "中性" if trend != "--" else "--"
                )
                c2.metric("MACD 信号", trend_cn)

                rsi_val = rsi.get("value", 50)
                macd_hist = macd.get("histogram", 0) or 0
                if isinstance(rsi_val, (int, float)) and rsi_val < 30 and macd_hist > 0:
                    rec = "买入"
                elif isinstance(rsi_val, (int, float)) and rsi_val > 70 and macd_hist < 0:
                    rec = "卖出"
                else:
                    rec = "持有"

                badge_class = "buy" if rec == "买入" else "sell" if rec == "卖出" else "neutral"
                st.markdown(
                    f'<span class="score-badge {badge_class}" style="font-size: 1rem;">{rec}</span>',
                    unsafe_allow_html=True,
                )

            if st.button("查看完整分析", key="goto_full_analysis"):
                st.session_state.selected_symbol = quick_sym
                st.switch_page("pages/2_Stock_Analysis.py")
        else:
            st.error(f"未找到 '{quick_sym}' 的相关数据。")

# ─── 新闻流 ───────────────────────────────────────────────
st.markdown("---")
st.markdown("### 最新资讯")

news_symbol = st.session_state.get("selected_symbol", "") or "AAPL"
news = get_company_news(news_symbol)

if news:
    # 推荐文章（第一篇，全宽带缩略图）
    featured = news[0]
    render_news_card(
        title=featured.get("title", "未命名文章"),
        source=featured.get("source", ""),
        date=format_date(featured.get("published_at", "")),
        description=featured.get("description", ""),
        url=featured.get("url", ""),
        thumbnail=featured.get("thumbnail", ""),
        content_type=featured.get("type", ""),
    )

    # 其余文章按两列网格排列
    cols = st.columns(2)
    for i, article in enumerate(news[1:9]):
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
    st.caption(f"暂未找到 {news_symbol} 的近期新闻。")
