"""
分红分析 - 收益率、安全性评分、增长历史、
分类（分红之王/贵族）与收益率对比。
"""

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_gauge_chart, create_horizontal_bar

from utils.data_service import analyze_dividends, compare_dividends
from utils.formatters import format_currency, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="分红分析 | 智能金融 AI",
    page_icon=":moneybag:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 分红分析")
st.caption("分红安全性评分、增长追踪、收益率对比与价值投资洞察")

# 映射字典
SAFETY_RATING_CN = {
    "Very Safe": "极安全",
    "Safe": "安全",
    "Borderline Safe": "尚算安全",
    "Unsafe": "不安全",
    "Very Unsafe": "极不安全",
}
CLASS_CN = {
    "King": "分红之王",
    "Aristocrat": "分红贵族",
    "Champion": "分红冠军",
    "Contender": "分红竞争者",
    "Challenger": "分红挑战者",
}
RENAME_FACTORS = {
    "payout_ratio": "派息率",
    "earnings_stability": "盈利稳定性",
    "debt_to_equity": "资产负债率",
    "free_cash_flow": "自由现金流",
    "revenue_growth": "营收增长",
    "dividend_history": "分红历史",
    "interest_coverage": "利息保障倍数",
    "roe": "净资产收益率(ROE)",
}


def _class_cn(full_text: str) -> str:
    cn = full_text or ""
    for en, zh in CLASS_CN.items():
        cn = cn.replace(en, zh)
    return cn

# ─── 标签页 ────────────────────────────────────────────
tab1, tab2 = st.tabs(["单只股票分析", "多只对比"])

# ─── Tab 1: 单只股票 ────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = (
            st.text_input(
                "股票代码",
                value=st.session_state.get("selected_symbol", "JNJ"),
                placeholder="请输入代码（如 JNJ、KO、PG）",
                key="div_symbol",
            )
            .strip()
            .upper()
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("分析", use_container_width=True, type="primary", key="div_btn")

    if analyze_btn and symbol:
        st.session_state.div_active = symbol

    active = st.session_state.get("div_active", "")
    if active:
        with st.spinner(f"正在分析 {active} 的分红数据……"):
            data = analyze_dividends(active)

        if "error" in data:
            st.error(f"分析失败：{data['error']}")
        elif not data.get("pays_dividends", False):
            st.warning(data.get("message", f"{active} 当前不派发股息。"))
        else:
            name = data.get("name", active)
            current = data.get("current_dividend", {})
            safety = data.get("dividend_safety", {})
            growth = data.get("dividend_growth", {})
            yields = data.get("yield_comparison", {})

            # ── 头部信息 ──
            st.markdown(f"### {name} ({active})")

            # ── 核心指标行 ──
            mcols = st.columns(5)
            with mcols[0]:
                st.metric("股息率", f"{current.get('dividend_yield', 0):.2f}%")
            with mcols[1]:
                annual = current.get("annual_dividend", 0)
                st.metric("年度分红", f"${annual:.2f}" if annual else "--")
            with mcols[2]:
                payout = current.get("payout_ratio")
                st.metric("派息率", f"{payout:.1f}%" if payout else "--")
            with mcols[3]:
                st.metric("安全性得分", f"{safety.get('safety_score', 0)}/100")
            with mcols[4]:
                yrs = growth.get("consecutive_years_increased", 0)
                st.metric("连续增长年数", str(yrs) if yrs else "--")

            st.markdown("---")

            # ── 安全性 + 分类 ──
            scol1, scol2 = st.columns([1, 2])

            with scol1:
                score = safety.get("safety_score", 0)
                rating_en = safety.get("rating", "--")
                rating_cn = SAFETY_RATING_CN.get(rating_en, rating_en)
                cut_prob = safety.get("dividend_cut_probability", "--")

                color = (
                    COLORS.get("success", "#22c55e")
                    if score >= 70
                    else (
                        COLORS.get("warning", "#eab308")
                        if score >= 40
                        else COLORS.get("danger", "#ef4444")
                    )
                )

                st.markdown(
                    f"""
                <div style="text-align:center; padding:20px; border-radius:8px; border:1px solid {color};">
                    <div style="font-size:3em; font-weight:bold; color:{color};">{score}</div>
                    <div style="font-size:0.9em; color:{COLORS.get('text_secondary', '#a1a1aa')};">安全性得分</div>
                    <div style="font-size:1.1em; color:{color}; font-weight:bold; margin-top:4px;">{rating_cn}</div>
                    <div style="font-size:0.85em; color:{COLORS.get('text_muted', '#71717a')}; margin-top:4px;">削减概率：{cut_prob}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # 分类徽章
                classification = growth.get("classification", "")
                if classification:
                    badge_color = (
                        "#FFD700"
                        if "King" in classification
                        else (
                            "#C0C0C0"
                            if "Aristocrat" in classification
                            else (
                                "#CD7F32"
                                if "Champion" in classification
                                else COLORS.get("accent_primary", "#6366f1")
                            )
                        )
                    )
                    st.markdown(
                        f"""
                    <div style="text-align:center; margin-top:12px; padding:8px; border-radius:6px; background:{badge_color}20; border:1px solid {badge_color};">
                        <span style="color:{badge_color}; font-weight:bold;">{_class_cn(classification)}</span>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            with scol2:
                st.markdown("**安全性因子拆解**")
                factors = safety.get("factors", {})
                if factors:
                    factor_rows = []
                    for factor_name, factor_data in factors.items():
                        if isinstance(factor_data, dict):
                            # 中文名映射
                            fn_key = str(factor_name).lower()
                            cn_name = RENAME_FACTORS.get(fn_key, str(factor_name).replace("_", " ").title())
                            factor_rows.append(
                                {
                                    "因子": cn_name,
                                    "取值": factor_data.get("value", "--"),
                                    "评估": factor_data.get("assessment", ""),
                                }
                            )
                    if factor_rows:
                        st.dataframe(
                            pd.DataFrame(factor_rows), use_container_width=True, hide_index=True
                        )

                # 红色警告
                flags = safety.get("red_flags", [])
                if flags:
                    st.markdown("**风险提示：**")
                    for flag in flags:
                        st.markdown(f"- {flag}")
                else:
                    st.success("未检测到明显风险信号")

            st.markdown("---")

            # ── 分红增长 ──
            gcol1, gcol2 = st.columns(2)

            with gcol1:
                st.markdown("**分红增长记录**")
                cagr_3 = growth.get("cagr_3_year")
                cagr_5 = growth.get("cagr_5_year")
                cagr_10 = growth.get("cagr_10_year")
                last_inc = growth.get("last_increase_pct")

                growth_data = []
                if cagr_3 is not None:
                    growth_data.append({"周期": "3年年复合增速", "增长率": f"{cagr_3:.1f}%"})
                if cagr_5 is not None:
                    growth_data.append({"周期": "5年年复合增速", "增长率": f"{cagr_5:.1f}%"})
                if cagr_10 is not None:
                    growth_data.append({"周期": "10年年复合增速", "增长率": f"{cagr_10:.1f}%"})
                if last_inc is not None:
                    growth_data.append({"周期": "最近一次增幅", "增长率": f"{last_inc:.1f}%"})

                if growth_data:
                    st.dataframe(
                        pd.DataFrame(growth_data), use_container_width=True, hide_index=True
                    )

            with gcol2:
                st.markdown("**股息率对比**")
                stock_yield = yields.get("stock_yield", 0)
                sector_avg = yields.get("sector_average", 0)
                sp500_avg = yields.get("sp500_average", 0)
                treasury = yields.get("treasury_10y", 0)

                comparison_data = [
                    {"基准": f"{active}", "股息率 (%)": stock_yield or 0},
                    {
                        "基准": f"行业均值（{yields.get('sector', '--')}）",
                        "股息率 (%)": sector_avg or 0,
                    },
                    {"基准": "标普 500 均值", "股息率 (%)": sp500_avg or 0},
                    {"基准": "10 年期美债", "股息率 (%)": treasury or 0},
                ]
                comp_df = pd.DataFrame(comparison_data)
                st.bar_chart(
                    comp_df.set_index("基准"), color=COLORS.get("accent_primary", "#6366f1")
                )

                assessment = yields.get("yield_assessment", "")
                if assessment:
                    st.caption(assessment)

            st.markdown("---")

            # ── 发放详情 ──
            st.markdown("**发放详情**")
            dcols = st.columns(4)
            with dcols[0]:
                freq = current.get('frequency', '--')
                freq_cn = {
                    "Monthly": "月度",
                    "Quarterly": "季度",
                    "Semi-Annual": "半年度",
                    "Annual": "年度",
                }.get(freq, freq)
                st.markdown(f"**发放频率**：{freq_cn}")
            with dcols[1]:
                st.markdown(f"**最近一次发放金额**：${current.get('last_payment_amount', '--')}")
            with dcols[2]:
                st.markdown(f"**除息日**：{current.get('ex_dividend_date', '--')}")
            with dcols[3]:
                yrs = growth.get("consecutive_years_increased", 0)
                st.markdown(f"**连续增长年数**：{yrs} 年")

# ─── Tab 2: 对比 ──────────────────────────────────────────
with tab2:
    symbols_input = st.text_input(
        "对比股票（以逗号分隔）",
        value="JNJ, KO, PG, PEP, ABBV",
        placeholder="例如 JNJ、KO、PG、PEP、ABBV",
        key="div_compare_input",
    )
    compare_btn = st.button("对比分红画像", key="div_compare_btn", type="primary")

    if compare_btn and symbols_input:
        symbols = tuple(s.strip().upper() for s in symbols_input.split(",") if s.strip())
        if len(symbols) < 2:
            st.warning("请至少输入 2 只股票代码。")
        else:
            with st.spinner("正在对比各股分红画像……"):
                result = compare_dividends(symbols)

            if "error" in result:
                st.error(result["error"])
            else:
                comparison = result.get("comparison", [])
                if comparison:
                    st.markdown("### 分红对比")

                    # 构建汇总表
                    rows = []
                    for c in comparison:
                        if "error" in c:
                            continue
                        class_en = c.get("classification", "--")
                        rows.append(
                            {
                                "代码": c.get("symbol", ""),
                                "股息率 (%)": c.get("dividend_yield", 0),
                                "安全性得分": c.get("safety_score", 0),
                                "派息率 (%)": c.get("payout_ratio", 0),
                                "连续增长年数": c.get("consecutive_years_increased", 0),
                                "分类": CLASS_CN.get(class_en, class_en)
                                if not any(k in class_en for k in CLASS_CN.keys())
                                else _class_cn(class_en),
                                "5年复合增速 (%)": c.get("cagr_5_year", 0),
                            }
                        )

                    if rows:
                        df = pd.DataFrame(rows)
                        st.dataframe(
                            df.style.background_gradient(
                                subset=["安全性得分"], cmap="YlGn"
                            ).background_gradient(subset=["股息率 (%)"], cmap="YlOrRd"),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # 最佳结果
                    best = result.get("best_safety", {})
                    highest_yield = result.get("highest_yield", {})
                    if best:
                        st.markdown(
                            f"**最安全的分红**：{best.get('symbol', '--')} "
                            f"（安全性：{best.get('safety_score', 0)}/100）"
                        )
                    if highest_yield:
                        st.markdown(
                            f"**最高股息率**：{highest_yield.get('symbol', '--')} "
                            f"（{highest_yield.get('dividend_yield', 0):.2f}%）"
                        )

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "分红数据来源：Yahoo Finance。安全性评分为算法估算结果，仅供参考，不构成投资建议。"
)
