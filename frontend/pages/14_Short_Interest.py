"""
卖空兴趣分析 - 轧空评分、回补天数、历史背景
与多空双方风险评估。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

from utils.data_service import (
    compare_short_interest,
    get_short_interest,
    get_squeeze_watchlist,
)
from utils.formatters import format_large_number, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="卖空兴趣 | 智能金融 AI",
    page_icon=":chart_with_downwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 卖空兴趣分析")
st.caption("跟踪做空交易活跃度、轧空评分与多空风险评估")

# ─── 标签页 ────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["单只股票分析", "多只对比", "轧空观察名单"])

RISK_CN = {
    "Low": "低",
    "Elevated": "中等",
    "Moderate": "中等",
    "High": "高",
    "Extreme": "极高",
}
TREND_CN = {
    "rising": "上升",
    "falling": "下降",
    "stable": "稳定",
    "flat": "平坦",
    "increasing": "增加",
    "decreasing": "减少",
}
PERCENTILE_CN = {
    "Very High": "极高水平",
    "High": "高水平",
    "Above Average": "高于平均",
    "Average": "平均水平",
    "Below Average": "低于平均",
    "Low": "低水平",
    "Very Low": "极低水平",
}

# ─── Tab 1: 单只股票 ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = (
            st.text_input(
                "股票代码",
                value=st.session_state.get("selected_symbol", "GME"),
                placeholder="请输入代码（如 GME、AMC、TSLA）",
                key="si_symbol",
            )
            .strip()
            .upper()
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("分析", use_container_width=True, type="primary", key="si_btn")

    if analyze_btn and symbol:
        st.session_state.si_active = symbol

    active = st.session_state.get("si_active", "")
    if active:
        with st.spinner(f"正在分析 {active} 的卖空兴趣……"):
            data = get_short_interest(active)

        if "error" in data:
            st.error(f"分析失败：{data['error']}")
        else:
            si = data.get("short_interest", {})
            sq = data.get("squeeze_analysis", {})
            hist = data.get("historical_context", {})
            borrow = data.get("borrow_data", {})
            risk = data.get("risk_assessment", {})
            price = data.get("current_price", 0)

            # ── 头部指标 ──
            st.markdown(f"### {data.get('company_name', active)} ({active})")
            st.markdown(f"**当前价格**：${price:.2f}")

            mcols = st.columns(4)
            with mcols[0]:
                st.metric(
                    "流通股做空占比",
                    f"{si.get('short_percent_of_float', 0):.1f}%",
                    delta=f"环比 {si.get('change_vs_previous_pct', 0):+.1f}%",
                )
            with mcols[1]:
                st.metric("卖空股数", si.get("shares_short_formatted", "--"))
            with mcols[2]:
                st.metric("回补天数 (Days-to-Cover)", f"{si.get('short_ratio_days_to_cover', 0):.1f}")
            with mcols[3]:
                st.metric("轧空评分", f"{sq.get('squeeze_score', 0)}/100")

            st.markdown("---")

            # ── 轧空分析 ──
            scol1, scol2 = st.columns([1, 2])

            with scol1:
                score = sq.get("squeeze_score", 0)
                risk_level = sq.get("risk_level", "Low")
                risk_level_cn = RISK_CN.get(risk_level, risk_level)
                color = (
                    COLORS.get("danger", "#ef4444")
                    if risk_level == "High" or risk_level == "Extreme"
                    else (
                        COLORS.get("warning", "#eab308")
                        if risk_level == "Elevated" or risk_level == "Moderate"
                        else COLORS.get("success", "#22c55e")
                    )
                )
                st.markdown(
                    f"""
                <div style="text-align:center; padding:20px; border-radius:8px; border:1px solid {color};">
                    <div style="font-size:3em; font-weight:bold; color:{color};">{score}</div>
                    <div style="font-size:0.9em; color:{COLORS.get('text_secondary', '#a1a1aa')};">轧空评分</div>
                    <div style="font-size:1.2em; color:{color}; font-weight:bold; margin-top:4px;">{risk_level_cn} 风险</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with scol2:
                st.markdown("**轧空因子拆解**")
                factors = sq.get("factors", {})
                factor_df = pd.DataFrame(
                    [
                        {
                            "因子": "流通股做空占比",
                            "得分": factors.get("short_percent_score", 0),
                        },
                        {"因子": "回补天数", "得分": factors.get("days_to_cover_score", 0)},
                        {
                            "因子": "卖空量近期走势",
                            "得分": factors.get("recent_increase_score", 0),
                        },
                        {"因子": "融券成本", "得分": factors.get("borrow_cost_score", 0)},
                    ]
                )
                st.bar_chart(
                    factor_df.set_index("因子"), color=COLORS.get("accent_primary", "#6366f1")
                )

            st.markdown(f"**综合判断**：{sq.get('assessment', '')}")

            st.markdown("---")

            # ── 背景 + 融券数据 ──
            ccol1, ccol2 = st.columns(2)

            with ccol1:
                st.markdown("**历史背景**")
                pct_label_raw = hist.get("percentile_label", "")
                pct_label_cn = PERCENTILE_CN.get(pct_label_raw, pct_label_raw)
                st.markdown(
                    f"- **全市场百分位**：{hist.get('market_percentile', '--')} 位 — {pct_label_cn}"
                )
                trend_raw = str(hist.get("trend", "")).lower()
                trend_cn = TREND_CN.get(trend_raw, str(hist.get('trend', '--')).title())
                st.markdown(f"- **趋势**：{trend_cn}")
                st.markdown(
                    f"- **上月卖空股数**：{si.get('previous_month_formatted', '--')}"
                )
                st.markdown(f"- **环比变动**：{si.get('change_vs_previous_pct', 0):+.1f}%")

            with ccol2:
                st.markdown("**融券数据（估算）**")
                st.markdown(
                    f"- **估算融券利率**：{borrow.get('estimated_borrow_rate_pct', 0):.1f}%"
                )
                st.markdown(f"- **可融性评估**：{borrow.get('borrow_assessment', '--')}")
                st.caption(borrow.get("note", ""))

            st.markdown("---")

            # ── 风险评估 ──
            st.markdown("**风险评估**")
            rcol1, rcol2 = st.columns(2)
            with rcol1:
                st.markdown("**对多头持仓者：**")
                st.info(risk.get("for_longs", "--"))
            with rcol2:
                st.markdown("**对空头持仓者：**")
                st.warning(risk.get("for_shorts", "--"))

            catalysts = risk.get("catalyst_watch", [])
            if catalysts:
                st.markdown("**重点关注催化剂：**")
                for c in catalysts:
                    st.markdown(f"- {c}")

            st.caption(data.get("data_freshness", ""))

# ─── Tab 2: 对比 ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "对比股票（以逗号分隔）",
        value="GME, AMC, TSLA, RIVN, NIO",
        placeholder="例如 GME、AMC、TSLA",
        key="si_compare_input",
    )
    compare_btn = st.button("对比卖空兴趣", key="si_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("请至少输入 2 只股票代码。")
        else:
            with st.spinner("正在对比卖空兴趣……"):
                result = compare_short_interest(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                ranking = result.get("ranking", [])
                if ranking:
                    st.markdown("### 轧空风险排名")
                    # 汉化排名表表头
                    rank_df = pd.DataFrame(ranking)
                    # 尝试重命名列（如果存在）
                    rename_map = {
                        "symbol": "代码",
                        "squeeze_score": "轧空评分",
                        "short_percent_of_float": "做空占流通股(%)",
                        "short_ratio_days_to_cover": "回补天数",
                        "risk_level": "风险等级",
                    }
                    rank_df = rank_df.rename(columns={k: v for k, v in rename_map.items() if k in rank_df.columns})
                    if "风险等级" in rank_df.columns:
                        rank_df["风险等级"] = rank_df["风险等级"].map(RISK_CN).fillna(rank_df["风险等级"])
                    score_col = "轧空评分" if "轧空评分" in rank_df.columns else "squeeze_score"
                    st.dataframe(
                        rank_df.style.background_gradient(subset=[score_col], cmap="YlOrRd"),
                        use_container_width=True,
                        hide_index=True,
                    )

                # 每只股票详情
                individual = result.get("individual", {})
                for sym, sdata in individual.items():
                    if "error" in sdata:
                        continue
                    with st.expander(
                        f"{sym} — 轧空评分：{sdata.get('squeeze_analysis', {}).get('squeeze_score', 0)}"
                    ):
                        si = sdata.get("short_interest", {})
                        risk_en = sdata.get("squeeze_analysis", {}).get("risk_level", "--")
                        st.markdown(
                            f"**做空占流通股**：{si.get('short_percent_of_float', 0):.1f}% | "
                            f"**回补天数**：{si.get('short_ratio_days_to_cover', 0):.1f} | "
                            f"**环比变动**：{si.get('change_vs_previous_pct', 0):+.1f}% | "
                            f"**风险**：{RISK_CN.get(risk_en, risk_en)}"
                        )

# ─── Tab 3: 轧空观察名单 ────────────────────────────────
with tab3:
    st.markdown("### 潜在轧空标的扫描")
    st.caption("从热门股票中筛选具备轧空潜力的标的")

    min_score = st.slider("轧空评分下限", 0, 100, 50, 5, key="si_min_score")
    scan_btn = st.button("扫描轧空候选", key="si_scan_btn", type="primary")

    if scan_btn:
        with st.spinner("正在扫描股票轧空潜力……"):
            result = get_squeeze_watchlist(min_score)

        if "error" in result:
            st.error(result["error"])
        else:
            candidates = result.get("candidates", [])
            st.markdown(
                f"**找到 {len(candidates)} 只候选**（共扫描 {result.get('screened', 0)} 只股票）"
            )

            if candidates:
                df = pd.DataFrame(candidates)
                rename_map = {
                    "symbol": "代码",
                    "company_name": "公司名",
                    "squeeze_score": "轧空评分",
                    "short_percent_of_float": "做空占流通股(%)",
                    "days_to_cover": "回补天数",
                    "risk_level": "风险等级",
                }
                df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
                if "风险等级" in df.columns:
                    df["风险等级"] = df["风险等级"].map(RISK_CN).fillna(df["风险等级"])
                score_col = "轧空评分" if "轧空评分" in df.columns else "squeeze_score"
                st.dataframe(
                    df.style.background_gradient(subset=[score_col], cmap="YlOrRd"),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info(f"未找到轧空评分 ≥ {min_score} 的股票。")

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "卖空数据由交易所每两周报告一次，通常存在约 10 天的延迟。轧空评分仅作参考，不构成投资建议。"
)
