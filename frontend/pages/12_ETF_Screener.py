"""
ETF 推荐 - 基于全面主题分析、由 AI 评分排序的 ETF 精选建议。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_grouped_bar, create_horizontal_bar

from utils.data_service import screen_etfs
from utils.formatters import format_currency, format_large_number, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, get_plotly_layout, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="ETF 推荐 | 智能金融 AI",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## ETF 智能推荐")
st.caption("基于 AI 深度分析 17 个投资主题、筛选综合得分前 10 的 ETF 标的")

# ─── 自动运行全量分析 ──────────────────────────────────

with st.spinner("正在分析 17 个投资主题并为 ETF 综合打分……"):
    result = screen_etfs(top_n=10)

if "error" in result:
    st.error(f"分析失败：{result['error']}")
    st.stop()

top_recs = result.get("top_recommendations", [])
all_etfs = result.get("all_etfs", [])
theme_rankings = result.get("theme_rankings", [])

if not top_recs:
    st.warning("当前暂不可用 ETF 数据，请稍后再试。")
    st.stop()

# ─── 汇总 KPI ────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)
k1.metric("已分析主题数", result.get("total_themes_analyzed", 0))
k2.metric("已筛选 ETF", result.get("total_etfs_screened", 0))
k3.metric("最佳推荐", top_recs[0]["symbol"] if top_recs else "--")
k4.metric(
    "最佳得分",
    f"{top_recs[0]['composite_score']}/100" if top_recs else "--",
)


# ─── 章节标题助手 ───────────────────────────────────


def _section(title: str):
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1.5rem 0 1rem;">
            <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
            <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem;
                        font-weight: 600; letter-spacing: -0.01em;">{title}</h3>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── 前 10 推荐卡片 ────────────────────────────

_section("推荐前 10 名 ETF")

REC_COLORS = {
    "Strong Buy": "#22c55e",
    "Buy": "#4ade80",
    "Hold": "#eab308",
    "Underweight": "#f97316",
    "Avoid": "#ef4444",
}

# 评级中文
REC_CN = {
    "Strong Buy": "强烈买入",
    "Buy": "买入",
    "Hold": "持有",
    "Underweight": "减持",
    "Avoid": "回避",
}

# 风险等级中文
RISK_CN = {
    "Low": "低风险",
    "Medium": "中风险",
    "High": "高风险",
}

for row_start in range(0, len(top_recs), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        idx = row_start + j
        if idx >= len(top_recs):
            break
        etf = top_recs[idx]
        rank = idx + 1

        rec = etf.get("recommendation", "Hold")
        rec_cn = REC_CN.get(rec, rec)
        rc = REC_COLORS.get(rec, "#a1a1aa")

        returns = etf.get("returns", {})
        ret_1y = returns.get("1y")
        ret_1y_str = format_percent(ret_1y) if ret_1y is not None else "--"
        ret_1y_color = "#22c55e" if (ret_1y or 0) >= 0 else "#ef4444"

        ret_3m = returns.get("3m")
        ret_3m_str = format_percent(ret_3m) if ret_3m is not None else "--"
        ret_3m_color = "#22c55e" if (ret_3m or 0) >= 0 else "#ef4444"

        ret_ytd = returns.get("ytd")
        ret_ytd_str = format_percent(ret_ytd) if ret_ytd is not None else "--"
        ret_ytd_color = "#22c55e" if (ret_ytd or 0) >= 0 else "#ef4444"

        expense = etf.get("expense_ratio")
        expense_str = f"{expense * 100:.2f}%" if expense else "--"

        assets = etf.get("total_assets")
        assets_str = format_large_number(assets) if assets else "--"

        vol = etf.get("volatility")
        vol_str = f"{vol:.1f}%" if vol else "--"

        risk_en = etf.get("risk_level", "")
        risk_cn = RISK_CN.get(risk_en, risk_en)

        with col:
            st.markdown(
                f"""
                <div class="card" style="position: relative; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; padding: 0.35rem 0.7rem;
                                background: rgba(99, 102, 241, 0.1); color: #818cf8; font-size: 0.7rem;
                                font-weight: 700; border-radius: 16px 0 8px 0; font-family: 'IBM Plex Mono', monospace;">
                        #{rank}
                    </div>
                    <div style="position: absolute; top: 0; right: 0; padding: 0.35rem 0.75rem;
                                background: {rc}12; color: {rc}; font-size: 0.65rem;
                                font-weight: 600; border-radius: 0 16px 0 8px; border-left: 1px solid {rc}25;
                                border-bottom: 1px solid {rc}25; font-family: 'IBM Plex Mono', monospace;">
                        {rec_cn}
                    </div>
                    <div style="padding-top: 0.25rem;">
                        <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.125rem;">
                            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 1.2rem;
                                         font-weight: 700; color: #fafafa;">{etf['symbol']}</span>
                            <span style="font-size: 0.85rem; font-weight: 600; color: #6366f1;">
                                {etf['composite_score']}/100
                            </span>
                        </div>
                        <div style="font-size: 0.78rem; color: #a1a1aa; margin-bottom: 0.375rem;
                                    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90%;">
                            {etf.get('name', etf['symbol'])}
                        </div>
                        <div style="font-size: 0.675rem; color: #52525b; margin-bottom: 0.75rem;">
                            {etf.get('theme', '')} &middot; {risk_cn}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;
                                padding: 0.625rem 0; border-top: 1px solid rgba(255,255,255,0.06);
                                border-bottom: 1px solid rgba(255,255,255,0.06);">
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">年初至今</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_ytd_color};">{ret_ytd_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">3月</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_3m_color};">{ret_3m_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">1年</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
                                        font-weight: 600; color: {ret_1y_color};">{ret_1y_str}</div>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; padding-top: 0.5rem;">
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">费率</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{expense_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">规模</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{assets_str}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.6rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.04em;">波动率</div>
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #a1a1aa;">{vol_str}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─── 业绩对比图 ────────────────────────────

_section("业绩对比")

horizon_labels = ["1周", "1月", "3月", "6月", "1年", "年初至今"]
horizon_keys = ["1w", "1m", "3m", "6m", "1y", "ytd"]
chart_colors = [
    "#6366f1",
    "#8b5cf6",
    "#22c55e",
    "#eab308",
    "#ef4444",
    "#3b82f6",
    "#ec4899",
    "#14b8a6",
    "#f97316",
    "#06b6d4",
]

series_data = []
for i, etf in enumerate(top_recs):
    returns = etf.get("returns", {})
    values = [returns.get(k) or 0 for k in horizon_keys]
    series_data.append(
        {
            "name": etf["symbol"],
            "values": values,
            "color": chart_colors[i % len(chart_colors)],
        }
    )

fig = create_grouped_bar(horizon_labels, series_data, title="各周期收益率 (%)", height=420)
st.plotly_chart(fig, use_container_width=True)

# ─── 综合得分排名 ─────────────────────────────────

_section("综合得分排名")

score_etfs = list(reversed(top_recs))
score_labels = [e["symbol"] for e in score_etfs]
score_values = [e["composite_score"] for e in score_etfs]
score_colors = []
for s in score_values:
    if s >= 75:
        score_colors.append("#22c55e")
    elif s >= 60:
        score_colors.append("#4ade80")
    elif s >= 45:
        score_colors.append("#eab308")
    else:
        score_colors.append("#ef4444")

fig_scores = create_horizontal_bar(
    score_labels, score_values, title="综合得分 (0-100)", colors=score_colors
)
fig_scores.update_layout(height=max(280, len(score_etfs) * 36 + 80))
st.plotly_chart(fig_scores, use_container_width=True)

# ─── 主题排名 ──────────────────────────────────────────

if theme_rankings:
    _section("主题排名")

    STAGE_CN = {
        "Emerging": "萌芽期",
        "Growth": "成长期",
        "Mature": "成熟期",
        "Early": "早期",
    }

    theme_df = pd.DataFrame(
        [
            {
                "主题": t["theme_name"],
                "健康度": t["health_score"],
                "动量": t["momentum_score"],
                "风险等级": RISK_CN.get(t.get("risk_level", ""), t.get("risk_level", "")),
                "近1年表现": t.get("performance_1y", "--"),
                "年初至今": t.get("performance_ytd", "--"),
                "发展阶段": STAGE_CN.get(t.get("growth_stage", ""), t.get("growth_stage", "")),
            }
            for t in theme_rankings
        ]
    )

    st.dataframe(
        theme_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "健康度": st.column_config.ProgressColumn(
                "健康度", min_value=0, max_value=100, format="%d"
            ),
            "动量": st.column_config.ProgressColumn(
                "动量", min_value=0, max_value=100, format="%d"
            ),
        },
    )

# ─── 全部已筛选 ETF ───────────────────────────────────────

with st.expander("查看全部已筛选 ETF", expanded=False):
    full_df = pd.DataFrame(
        [
            {
                "代码": e["symbol"],
                "名称": e.get("name", ""),
                "主题": e.get("theme", ""),
                "综合得分": e["composite_score"],
                "评级": REC_CN.get(e.get("recommendation", ""), e.get("recommendation", "")),
                "现价": format_currency(e.get("current_price")),
                "1月": format_percent(e.get("returns", {}).get("1m")),
                "3月": format_percent(e.get("returns", {}).get("3m")),
                "1年": format_percent(e.get("returns", {}).get("1y")),
                "波动率": f"{e['volatility']:.1f}%" if e.get("volatility") else "--",
                "风险": RISK_CN.get(e.get("risk_level", ""), e.get("risk_level", "")),
            }
            for e in all_etfs
        ]
    )
    st.dataframe(full_df, use_container_width=True, hide_index=True)

# ─── 评分方法说明 ─────────────────────────────────────────────

with st.expander("评分方法说明", expanded=False):
    st.markdown(
        """
**综合得分 (0-100)** 由以下五项加权因子计算得出：

| 因子 | 权重 | 说明 |
|------|------|------|
| 主题健康度 | 30% | 对应投资主题的整体基本面健康评分 |
| 主题动量 | 20% | 主题成分股短期/中期/长期动量得分 |
| ETF 近 3 月收益 | 20% | 最新 3 个月 ETF 价格表现 |
| ETF 近 1 年收益 | 15% | 更长期 1 年价格走势 |
| 波动率 | 15% | 年化波动率越低得分越高 |

**评级区间：** 强烈买入 (75+)、买入 (60-74)、持有 (45-59)、减持 (30-44)、回避 (<30)

数据来源：Yahoo Finance。分析覆盖 17 个投资主题和约 50 只参考 ETF。
本页面内容仅供参考，不构成任何投资建议。
    """
    )


# ─── AI 顾问引导 ─────────────────────────────────────────

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
_section("有疑问？咨询 AI 顾问")

st.markdown(
    """
    <div class="card" style="text-align: center; padding: 1.5rem;">
        <div style="font-size: 0.95rem; font-weight: 600; color: #fafafa; margin-bottom: 0.375rem;">
            向 AI 顾问咨询任意 ETF、股票或投资策略
        </div>
        <div style="font-size: 0.8rem; color: #71717a;">
            获得个性化买入/卖出建议、持有期建议、风险分析与投资组合优化
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.button("打开 AI 顾问", use_container_width=True):
    st.switch_page("app.py")
