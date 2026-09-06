"""
增强新闻与舆情分析 - FinBERT/VADER 情绪打分、
新闻量跟踪、舆情趋势、来源多样性与主题提取。
"""

import streamlit as st
from components.header import render_header
from components.plotly_charts import (
    create_donut_chart,
    create_gauge_chart,
    create_horizontal_bar,
    create_line_chart,
)

from utils.data_service import analyze_news_sentiment
from utils.formatters import format_date, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="舆情分析 | 智能金融 AI",
    page_icon=":newspaper:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 新闻与舆情分析")
st.caption("基于 AI 的情绪评分、新闻量追踪、趋势研判与来源多样性分析")

# ─── 股票输入 ────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    symbol = (
        st.text_input(
            "股票代码",
            value=st.session_state.get("selected_symbol", "AAPL"),
            placeholder="请输入代码（如 AAPL）",
            key="sent_symbol",
        )
        .strip()
        .upper()
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("分析舆情", use_container_width=True, type="primary")

if analyze_btn and symbol:
    st.session_state.sent_symbol_active = symbol

active = st.session_state.get("sent_symbol_active", "")
if not active:
    st.info("请输入股票代码并点击 **分析舆情** 开始。")
    st.stop()

# ─── 获取数据 ──────────────────────────────────────────────
result = analyze_news_sentiment(active)

if "error" in result:
    st.error(f"错误：{result['error']}")
    st.stop()

agg = result.get("aggregate_sentiment", {})
dist = result.get("distribution", {})
volume = result.get("volume", {})
sources = result.get("source_diversity", {})
trend = result.get("sentiment_trend", {})
topics = result.get("topics", [])
correlation = result.get("news_price_correlation", {})
engine = result.get("engine", "unknown")

# ─── 头部信息 ──────────────────────────────────────────────────
agg_score = agg.get("score", 0)
agg_label = agg.get("label", "Neutral")
agg_conf = agg.get("confidence", 0)

# 情绪标签映射
LABEL_CN = {
    "Positive": "正面",
    "Negative": "负面",
    "Neutral": "中性",
    "Bearish": "看跌",
    "Bullish": "看涨",
}
agg_label_cn = LABEL_CN.get(agg_label, agg_label)

if agg_label == "Positive" or agg_label == "Bullish":
    label_color = COLORS["success"]
elif agg_label == "Negative" or agg_label == "Bearish":
    label_color = COLORS["danger"]
else:
    label_color = COLORS["text_muted"]

engine_label = (
    "FinBERT (金融领域专用)"
    if engine == "finbert"
    else "VADER (金融增强版)" if engine == "vader" else engine
)

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
            已分析 {result.get('articles_analyzed', 0)} 篇文章
        </span>
    </div>
    <div style="margin-left: auto; text-align: right;">
        <span style="font-size: 1.25rem; font-weight: 600; color: {label_color}; font-family: 'JetBrains Mono', monospace;">
            {agg_label_cn}
        </span>
        <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">分析引擎：{engine_label}</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 章节标题助手 ──────────────────────────────────────────


def section_header(title):
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; margin-top: 0.5rem;">
        <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
        <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: {COLORS['text_primary']}; font-size: 0.9rem; font-weight: 600;">
            {title}
        </h3>
        <div style="flex: 1; height: 1px; background: linear-gradient(90deg, {COLORS['border']}, transparent);"></div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ─── 总体情绪 ────────────────────────────────────
section_header("综合舆情")

g1, g2, g3, g4 = st.columns(4)

with g1:
    # 将 [-1, 1] 映射到 [0, 100]
    gauge_val = (agg_score + 1) / 2 * 100
    fig = create_gauge_chart(
        value=round(gauge_val, 1),
        title="舆情综合得分",
        min_val=0,
        max_val=100,
        ranges=[
            {"range": [0, 30], "color": "rgba(239, 68, 68, 0.3)"},
            {"range": [30, 45], "color": "rgba(245, 158, 11, 0.3)"},
            {"range": [45, 55], "color": "rgba(161, 161, 170, 0.2)"},
            {"range": [55, 70], "color": "rgba(59, 130, 246, 0.3)"},
            {"range": [70, 100], "color": "rgba(16, 185, 129, 0.3)"},
        ],
        height=220,
    )
    st.plotly_chart(fig, use_container_width=True)

with g2:
    st.metric("原始得分", f"{agg_score:+.3f}")
    st.metric("置信度", format_percent(agg_conf * 100, include_sign=False))
    tw = agg.get("time_weighted_score", 0)
    st.metric("时间加权得分", f"{tw:+.3f}")

with g3:
    if dist:
        fig = create_donut_chart(
            labels=["正面", "中性", "负面"],
            values=[dist.get("positive", 0), dist.get("neutral", 0), dist.get("negative", 0)],
            title="情绪分布",
            colors=[COLORS["success"], COLORS.get("text_muted", "#71717a"), COLORS["danger"]],
            height=220,
        )
        st.plotly_chart(fig, use_container_width=True)

with g4:
    if dist:
        st.metric("正面", f"{dist.get('positive', 0)} ({dist.get('positive_pct', 0)}%)")
        st.metric("中性", f"{dist.get('neutral', 0)} ({dist.get('neutral_pct', 0)}%)")
        st.metric("负面", f"{dist.get('negative', 0)} ({dist.get('negative_pct', 0)}%)")

st.markdown("<br>", unsafe_allow_html=True)

# ─── 新闻量 ────────────────────────────────────────────
section_header("新闻发布量")

v1, v2, v3, v4 = st.columns(4)
v1.metric("近 24 小时", volume.get("last_24h", 0))
v2.metric("近 48 小时", volume.get("last_48h", 0))
v3.metric("近 7 日", volume.get("last_7d", 0))
v4.metric("日均", volume.get("avg_daily", 0))

spike = volume.get("spike_detected", False)
assessment = volume.get("spike_assessment", "新闻量处于正常区间")
# 简单汉化
def _vol_cn(txt):
    t = txt or ""
    return (
        t
        .replace("Normal news flow", "新闻量处于正常区间")
        .replace("Elevated", "新闻量偏高")
        .replace("High", "新闻量显著增加")
        .replace("Spike", "新闻量异常飙升")
    )

if spike:
    st.warning(f"检测到新闻量异常：{_vol_cn(assessment)}")
else:
    st.caption(_vol_cn(assessment))

st.markdown("<br>", unsafe_allow_html=True)

# ─── 舆情趋势 ────────────────────────────────────────
if trend.get("values"):
    section_header("舆情趋势")

    tc1, tc2 = st.columns([1, 3])
    with tc1:
        direction = trend.get("direction", "Stable")
        momentum = trend.get("momentum", "No clear trend")

        def _dir_cn(d):
            return (
                (d or "")
                .replace("Improving", "改善")
                .replace("Deteriorating", "恶化")
                .replace("Stable", "稳定")
                .replace("Fluctuating", "震荡")
                or "稳定"
            )

        def _mom_cn(m):
            return (
                (m or "")
                .replace("No clear trend", "暂无明显趋势")
                .replace("Gaining", "动能增强")
                .replace("Losing", "动能减弱")
                .replace("strong", "强劲")
                .replace("weak", "疲软")
                or "暂无明显趋势"
            )

        direction_cn = _dir_cn(direction)
        momentum_cn = _mom_cn(momentum)
        if "改善" in direction_cn:
            dir_color = COLORS["success"]
        elif "恶化" in direction_cn:
            dir_color = COLORS["danger"]
        else:
            dir_color = COLORS["text_muted"]
        st.markdown(
            f"""
        <div style="padding: 1rem; background: {COLORS['bg_card']}; border-radius: 8px; border: 1px solid {COLORS['border']};">
            <div style="font-size: 0.75rem; color: {COLORS['text_muted']};">整体方向</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: {dir_color};">{direction_cn}</div>
            <div style="font-size: 0.75rem; color: {COLORS['text_muted']}; margin-top: 0.75rem;">动能强度</div>
            <div style="font-size: 0.85rem; color: {COLORS['text_secondary']};">{momentum_cn}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with tc2:
        fig = create_line_chart(
            dates=trend.get("dates", []),
            values=trend.get("values", []),
            title="每日平均舆情得分",
            fill=True,
            height=280,
            y_suffix="",
            show_zero_line=True,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─── 主题与来源多样性 ──────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    if topics:
        section_header("热门话题")
        labels = [t["topic"].replace("_", " ").title() for t in topics]
        values = [t["mentions"] for t in topics]
        colors = [COLORS.get("accent_primary", "#6366f1")] * len(labels)
        fig = create_horizontal_bar(
            labels=labels,
            values=values,
            title="话题出现频次",
            colors=colors,
        )
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    if sources.get("source_breakdown"):
        section_header("来源多样性")
        breakdown = sources["source_breakdown"]
        fig = create_donut_chart(
            labels=list(breakdown.keys()),
            values=list(breakdown.values()),
            title=f"{sources.get('unique_sources', 0)} 个来源",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(sources.get("assessment", ""))

st.markdown("<br>", unsafe_allow_html=True)

# ─── 头条文章 ───────────────────────────────────────────
section_header("最受关注的正面文章")
top_pos = result.get("top_positive", [])
if top_pos:
    for article in top_pos[:3]:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = LABEL_CN.get(sent.get("label", "Neutral"), sent.get("label", "中性"))
        conf = sent.get("confidence", 0)
        title = article.get("title", "无标题")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        score_color = (
            COLORS["success"]
            if score > 0
            else COLORS["danger"] if score < 0 else COLORS["text_muted"]
        )
        link = (
            f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>'
            if url
            else title
        )

        st.markdown(
            f"""
        <div style="padding: 0.75rem 1rem; background: {COLORS['bg_card']}; border-radius: 8px;
                    border: 1px solid {COLORS['border']}; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-size: 0.85rem; font-weight: 500;">{link}</div>
                    <div style="font-size: 0.7rem; color: {COLORS['text_muted']}; margin-top: 4px;">
                        {source} · {format_date(pub)}
                    </div>
                </div>
                <div style="text-align: right; min-width: 100px; margin-left: 1rem;">
                    <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: {score_color};">
                        {score:+.3f}
                    </span>
                    <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{label} · 置信度 {conf:.0%}</div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
else:
    st.caption("未找到显著正面的文章。")

st.markdown("<br>", unsafe_allow_html=True)

top_neg = result.get("top_negative", [])
if top_neg:
    section_header("最受关注的负面文章")
    for article in top_neg[:3]:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = LABEL_CN.get(sent.get("label", "Neutral"), sent.get("label", "中性"))
        conf = sent.get("confidence", 0)
        title = article.get("title", "无标题")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        score_color = (
            COLORS["success"]
            if score > 0
            else COLORS["danger"] if score < 0 else COLORS["text_muted"]
        )
        link = (
            f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>'
            if url
            else title
        )

        st.markdown(
            f"""
        <div style="padding: 0.75rem 1rem; background: {COLORS['bg_card']}; border-radius: 8px;
                    border: 1px solid {COLORS['border']}; margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <div style="font-size: 0.85rem; font-weight: 500;">{link}</div>
                    <div style="font-size: 0.7rem; color: {COLORS['text_muted']}; margin-top: 4px;">
                        {source} · {format_date(pub)}
                    </div>
                </div>
                <div style="text-align: right; min-width: 100px; margin-left: 1rem;">
                    <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: {score_color};">
                        {score:+.3f}
                    </span>
                    <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{label} · 置信度 {conf:.0%}</div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─── 全部评分文章 ────────────────────────────────────
all_articles = result.get("scored_articles", [])
if all_articles:
    section_header(f"全部已评分文章（共 {len(all_articles)} 篇）")

    for article in all_articles:
        sent = article.get("sentiment", {})
        score = sent.get("score", 0)
        label = LABEL_CN.get(sent.get("label", "Neutral"), sent.get("label", "中性"))
        title = article.get("title", "无标题")
        source = article.get("source", "")
        pub = article.get("published_at", "")
        url = article.get("url", "")

        if score >= 0.15:
            badge_bg = "rgba(34, 197, 94, 0.15)"
            badge_color = COLORS["success"]
        elif score <= -0.15:
            badge_bg = "rgba(239, 68, 68, 0.15)"
            badge_color = COLORS["danger"]
        else:
            badge_bg = "rgba(161, 161, 170, 0.1)"
            badge_color = COLORS["text_muted"]

        link = (
            f'<a href="{url}" target="_blank" style="color: {COLORS["text_primary"]}; text-decoration: none;">{title}</a>'
            if url
            else title
        )

        st.markdown(
            f"""
        <div style="padding: 0.6rem 1rem; border-bottom: 1px solid {COLORS['border']}; display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 600;
                         color: {badge_color}; background: {badge_bg}; padding: 2px 8px; border-radius: 4px; min-width: 55px; text-align: center;">
                {score:+.2f}
            </span>
            <div style="flex: 1;">
                <div style="font-size: 0.8rem;">{link}</div>
                <div style="font-size: 0.65rem; color: {COLORS['text_muted']};">{source} · {format_date(pub)}</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"""
<div style="text-align: center; padding: 1rem; border-top: 1px solid {COLORS['border']};">
    <p style="font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: {COLORS['text_muted']};">
        舆情引擎：{engine_label} · 新闻来源：Yahoo Finance · 情绪得分区间为 -1（看跌）到 +1（看涨）
    </p>
</div>
""",
    unsafe_allow_html=True,
)
