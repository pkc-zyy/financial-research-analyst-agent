"""
宏观经济看板 - FRED 宏观数据、美债收益率曲线、
利率环境分析与行业影响评估。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

from utils.formatters import format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="宏观经济 | 智能金融 AI",
    page_icon=":globe_with_meridians:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 宏观经济看板")
st.caption("核心经济指标、国债收益率曲线与利率环境分析（数据来源：FRED）")

# ─── 数据获取助手 ─────────────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def _get_macro_summary():
    from src.tools.macro_data import get_macro_summary

    return get_macro_summary()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_treasury_yields():
    from src.tools.macro_data import get_treasury_yields

    return get_treasury_yields()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_rate_env():
    from src.tools.macro_data import get_rate_environment

    return get_rate_environment()


@st.cache_data(ttl=1800, show_spinner=False)
def _get_macro_context(symbol: str):
    from src.tools.macro_data import get_macro_context_for_stock

    return get_macro_context_for_stock(symbol)


# ─── 主要内容 ────────────────────────────────────────────

with st.spinner("正在从 FRED 加载宏观经济数据……"):
    macro = _get_macro_summary()
    yields = _get_treasury_yields()
    rate_env = _get_rate_env()

# 检查可用性
if macro.get("source") == "unavailable":
    st.warning(
        "FRED API 尚未配置。请在 `.env` 文件中设置 `FRED_API_KEY` 以启用宏观数据。\n"
        "您可以前往 [fred.stlouisfed.org/docs/api](https://fred.stlouisfed.org/docs/api/api_key.html) 免费申请 API Key。"
    )
    st.stop()

# ─── 核心指标行 ─────────────────────────────────────
st.markdown("### 核心经济指标")

indicators = macro.get("indicators", {})

cols = st.columns(4)

indicator_display = [
    ("联邦基金利率", "federal_funds_rate", "%"),
    ("CPI 同比", "cpi_yoy", "%"),
    ("失业率", "unemployment", "%"),
    ("GDP 增速", "gdp_growth", "%"),
]

for i, (label, key, suffix) in enumerate(indicator_display):
    with cols[i]:
        data = indicators.get(key, {})
        current = data.get("current", "--")
        direction = data.get("direction", "")
        arrow = "▲" if direction == "rising" else "▼" if direction == "falling" else "→"
        dir_cn = (
            direction
            .replace("rising", "上升")
            .replace("falling", "下降")
            .replace("flat", "持平")
            or "持平"
        )
        color = (
            COLORS.get("accent_red", "#ff4444")
            if direction == "rising" and key in ("cpi_yoy", "unemployment")
            else (
                COLORS.get("accent_green", "#00cc66")
                if direction == "falling" and key in ("cpi_yoy", "unemployment")
                else (
                    COLORS.get("accent_green", "#00cc66")
                    if direction == "rising" and key == "gdp_growth"
                    else COLORS.get("text_secondary", "#888")
                )
            )
        )
        if isinstance(current, (int, float)):
            display_val = f"{current:.2f}{suffix}"
        else:
            display_val = str(current)
        st.metric(label=label, value=display_val, delta=f"{arrow} {dir_cn}")

# 第二行
cols2 = st.columns(4)
indicator_display_2 = [
    ("消费者信心指数", "consumer_confidence", ""),
    ("制造业 PMI", "pmi", ""),
    ("新屋开工", "housing_starts", "K"),
]
for i, (label, key, suffix) in enumerate(indicator_display_2):
    with cols2[i]:
        data = indicators.get(key, {})
        current = data.get("current", "--")
        direction = data.get("direction", "")
        arrow = "▲" if direction == "rising" else "▼" if direction == "falling" else "→"
        dir_cn = (
            direction
            .replace("rising", "上升")
            .replace("falling", "下降")
            .replace("flat", "持平")
            or "持平"
        )
        if isinstance(current, (int, float)):
            display_val = f"{current:.1f}{suffix}"
        else:
            display_val = str(current)
        st.metric(label=label, value=display_val, delta=f"{arrow} {dir_cn}")

st.markdown("---")

# ─── 国债收益率 ────────────────────────────────────────
st.markdown("### 国债收益率与收益率曲线")

ycol1, ycol2 = st.columns([2, 1])

with ycol1:
    yield_data = yields.get("yields", {})
    if yield_data:
        yield_df = pd.DataFrame(
            [
                {"期限": "2年期", "收益率 (%)": yield_data.get("2y", 0)},
                {"期限": "10年期", "收益率 (%)": yield_data.get("10y", 0)},
                {"期限": "30年期", "收益率 (%)": yield_data.get("30y", 0)},
            ]
        )
        st.bar_chart(yield_df.set_index("期限"), color=COLORS.get("accent_blue", "#4488ff"))

with ycol2:
    spread = yields.get("spread_2y_10y", 0)
    curve_status = yields.get("curve_status", "unknown")

    status_color = (
        COLORS.get("accent_green", "#00cc66")
        if curve_status == "normal"
        else (
            COLORS.get("accent_red", "#ff4444")
            if curve_status == "inverted"
            else COLORS.get("accent_yellow", "#ffaa00")
        )
    )
    curve_cn = {
        "normal": "正常",
        "inverted": "倒挂",
        "flat": "平坦",
        "unknown": "未知",
    }.get(curve_status, curve_status)

    st.markdown(
        f"""
    **2Y-10Y 利差**: `{spread:.2f}%`

    **曲线形态**: <span style="color:{status_color};font-weight:bold">{curve_cn.upper()}</span>
    """,
        unsafe_allow_html=True,
    )

    if curve_status == "inverted":
        st.error("收益率曲线倒挂 —— 历史上是领先的衰退预警信号。")
    elif curve_status == "flat":
        st.warning("收益率曲线平坦 —— 预示经济不确定性升高。")
    else:
        st.success("收益率曲线正常 —— 与经济扩张期表现一致。")

st.markdown("---")

# ─── 利率环境 ───────────────────────────────────────
st.markdown("### 利率环境分析")

rcol1, rcol2 = st.columns(2)

with rcol1:
    st.markdown("**美联储政策立场**")
    stance = rate_env.get("fed_stance", "unknown")
    real_rate = rate_env.get("real_rate", 0)
    inflation_trend = rate_env.get("inflation_trend", "stable")

    stance_icon = {"hiking": "📈", "cutting": "📉", "holding": "⏸️"}.get(stance, "❓")
    stance_cn = {"hiking": "加息中", "cutting": "降息中", "holding": "持观望望", "unknown": "未知"}.get(stance, stance.title())
    inflation_cn = (
        inflation_trend
        .replace("stable", "平稳")
        .replace("rising", "上升")
        .replace("falling", "下降")
        .replace("cooling", "降温")
        .replace("heating", "升温")
        .title()
    )
    st.markdown(f"- **立场**: {stance_icon} {stance_cn}")
    st.markdown(f"- **实际利率**: `{real_rate:.2f}%`（联邦基金利率 − CPI）")
    st.markdown(f"- **通胀趋势**: {inflation_cn}")

with rcol2:
    st.markdown("**各行业影响评估**")
    sector_impact = rate_env.get("sector_impact", {})
    if sector_impact:
        for sector, impact in sector_impact.items():
            direction = impact.get("direction", "neutral")
            icon = "🟢" if direction == "positive" else "🔴" if direction == "negative" else "⚪"
            st.markdown(f"- {icon} **{sector}**: {impact.get('assessment', '--')}")

st.markdown("---")

# ─── 个股宏观环境 ────────────────────────────────────
st.markdown("### 指定股票的宏观环境解读")
st.caption("查看当前宏观环境对某只股票所属行业的具体影响")

symbol = (
    st.text_input(
        "股票代码",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="请输入代码（如 AAPL）",
        key="macro_symbol",
    )
    .strip()
    .upper()
)

if symbol:
    with st.spinner(f"正在分析 {symbol} 的宏观环境……"):
        ctx = _get_macro_context(symbol)

    if ctx.get("source") == "unavailable":
        st.info("FRED API 未配置，无法执行个股宏观分析。")
    elif "error" in ctx:
        st.error(ctx["error"])
    else:
        sensitivity_cn = {
            "high": "高敏感",
            "low": "低敏感",
            "moderate": "中等敏感",
            "very high": "极高敏感",
            "neutral": "中性",
        }
        impact_cn = {
            "positive": "正面",
            "negative": "负面",
            "neutral": "中性",
            "mixed": "混合",
        }

        mcol1, mcol2 = st.columns(2)
        with mcol1:
            st.markdown(f"**所属行业**: {ctx.get('sector', '--')}")
            raw_sens = ctx.get('rate_sensitivity', '--')
            st.markdown(
                f"**利率敏感度**: {sensitivity_cn.get(str(raw_sens).lower(), raw_sens)}"
            )
            raw_impact = ctx.get('impact_direction', '--')
            st.markdown(
                f"**宏观影响方向**: {impact_cn.get(str(raw_impact).lower(), raw_impact)}"
            )
        with mcol2:
            st.markdown(f"**综合评估**: {ctx.get('assessment', '--')}")
            factors = ctx.get("key_factors", [])
            if factors:
                st.markdown("**关键驱动因素**:")
                for f in factors:
                    st.markdown(f"- {f}")

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption("数据来源：美国联邦储备经济数据库 (FRED) | 每 30 分钟更新")
