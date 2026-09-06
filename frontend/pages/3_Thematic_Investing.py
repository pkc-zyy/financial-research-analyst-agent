"""
主题投资 - 浏览投资主题、分析表现、进行对比。
"""

import streamlit as st
from components.header import render_header
from components.metrics_cards import render_kpi_row
from components.plotly_charts import (
    create_donut_chart,
    create_gauge_chart,
    create_horizontal_bar,
    create_radar_chart,
)

from utils.data_service import analyze_theme, get_themes_list, refresh_themes_cache
from utils.formatters import format_currency, format_large_number, format_percent
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="主题投资 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 主题投资")
st.caption("探索投资主题与长期大趋势")

# ─── 主题浏览 ───────────────────────────────────────────

# 首次加载时从磁盘刷新主题缓存
if "themes_refreshed" not in st.session_state:
    refresh_themes_cache()
    st.session_state.themes_refreshed = True

themes = get_themes_list()

_hdr1, _hdr2 = st.columns([3, 1])
with _hdr2:
    if st.button("刷新主题列表", use_container_width=True, key="refresh_themes_btn"):
        refresh_themes_cache()
        st.rerun()

if not themes:
    st.warning("无法加载投资主题，请确认 config/themes.yaml 文件存在。")
    st.stop()

# 模式切换
mode = st.radio(
    "模式", ["浏览与分析", "主题对比"], horizontal=True, label_visibility="collapsed"
)

if mode == "浏览与分析":
    # ─── 主题选择网格 ────────────────────────────────
    st.markdown("### 选择主题")

    cols = st.columns(2)
    for i, theme in enumerate(themes):
        with cols[i % 2]:
            risk = theme.get("risk_level", "Medium")
            risk_class = (
                "risk-high"
                if "high" in risk.lower()
                else "risk-low" if "low" in risk.lower() else "risk-medium"
            )
            risk_cn = (
                "高风险" if "high" in risk.lower()
                else "低风险" if "low" in risk.lower() else "中等风险"
            )
            stage_cn_map = {
                "Emerging": "萌芽期", "Growth": "成长期", "Mature": "成熟期", "Early": "早期",
            }
            stage = theme.get("growth_stage", "")
            stage_cn = stage_cn_map.get(stage, stage)

            tags_html = "".join(
                [f'<span class="tag">{tag}</span>' for tag in theme.get("sector_tags", [])[:3]]
            )
            tags_html += f'<span class="tag {risk_class}">{risk_cn}</span>'

            st.markdown(
                f"""
                <div class="theme-card">
                    <div class="theme-name">{theme.get('name', '未知主题')}</div>
                    <div class="theme-desc">{theme.get('description', '')[:120]}……</div>
                    <div class="theme-tags">{tags_html}</div>
                    <div style="font-size: 0.7rem; color: #6b7280; margin-top: 0.5rem;">
                        {theme.get('constituent_count', 0)} 只成分股 · {stage_cn}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                f"分析「{theme.get('name', '')}」",
                key=f"theme_{theme.get('theme_id', i)}",
                use_container_width=True,
            ):
                st.session_state.selected_theme = theme.get("theme_id")
                st.rerun()

    # ─── 主题分析 ──────────────────────────────────────
    selected = st.session_state.get("selected_theme")
    if selected:
        st.markdown("---")
        with st.spinner(f"正在分析主题：{selected}……"):
            result = analyze_theme(selected)

        if "error" in result:
            st.error(f"主题分析出现错误：{result['error']}")
            st.stop()

        # 主题抬头
        st.markdown(f"### {result.get('theme', selected)}")
        st.caption(result.get("description", ""))

        # KPI 行
        perf = result.get("theme_performance", {})
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            fig = create_gauge_chart(
                value=result.get("theme_health_score", 0),
                title="主题健康分",
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            fig = create_gauge_chart(
                value=result.get("momentum_score", 0),
                title="动量得分",
                height=200,
            )
            st.plotly_chart(fig, use_container_width=True)

        c3.metric("1 年表现", perf.get("1y", "N/A"))
        c4.metric("年初至今 (YTD)", perf.get("ytd", "N/A"))

        # 多周期表现表
        st.markdown("#### 多周期表现")
        perf_cols = st.columns(6)
        horizons = [
            ("1 周", "1w"),
            ("1 月", "1m"),
            ("3 月", "3m"),
            ("6 月", "6m"),
            ("1 年", "1y"),
            ("YTD", "ytd"),
        ]
        for col, (label, key) in zip(perf_cols, horizons):
            val = perf.get(key, "N/A")
            col.metric(label=label, value=val)

        st.markdown("---")

        # 领涨 / 领跌
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 领涨成分股")
            top = result.get("top_performers", [])
            if top:
                labels = [t.get("symbol", "?") for t in top]
                values = []
                for t in top:
                    ret = t.get("1_year_return", "0%")
                    try:
                        values.append(float(str(ret).replace("%", "").replace("+", "")))
                    except ValueError:
                        values.append(0)
                colors = ["#10b981" if v >= 0 else "#ef4444" for v in values]
                fig = create_horizontal_bar(labels, values, title="1 年收益率 (%)", colors=colors)
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("#### 领跌成分股")
            laggards = result.get("laggards", [])
            if laggards:
                labels = [t.get("symbol", "?") for t in laggards]
                values = []
                for t in laggards:
                    ret = t.get("1_year_return", "0%")
                    try:
                        values.append(float(str(ret).replace("%", "").replace("+", "")))
                    except ValueError:
                        values.append(0)
                colors = ["#10b981" if v >= 0 else "#ef4444" for v in values]
                fig = create_horizontal_bar(labels, values, title="1 年收益率 (%)", colors=colors)
                st.plotly_chart(fig, use_container_width=True)

        # 行业分布
        sector_overlap = result.get("sector_overlap", {})
        if sector_overlap:
            st.markdown("#### 行业分布")
            labels = list(sector_overlap.keys())
            values = []
            for v in sector_overlap.values():
                try:
                    values.append(float(str(v).replace("%", "")))
                except ValueError:
                    values.append(0)
            fig = create_donut_chart(labels, values, title="行业占比")
            st.plotly_chart(fig, use_container_width=True)

        # 风险指标
        risk = result.get("theme_risk", {})
        if risk:
            st.markdown("#### 主题风险")
            c1, c2, c3 = st.columns(3)
            c1.metric("内部相关性", f"{risk.get('intra_correlation', 'N/A')}")
            div_score_str = risk.get("diversification_score", "N/A")
            div_cn = {"Low": "偏低", "Moderate": "中等", "Good": "良好", "Excellent": "优秀"}.get(
                div_score_str, div_score_str
            )
            c2.metric("分散度", div_cn)
            risk_level = result.get("risk_level", "N/A")
            risk_level_cn = (
                "高风险" if "high" in str(risk_level).lower()
                else "低风险" if "low" in str(risk_level).lower() else "中等风险"
            )
            c3.metric("风险等级", risk_level_cn)
            desc = risk.get("diversification_description", "")
            if desc:
                st.caption(desc)

        # 成分股详情
        details = result.get("constituent_details", {})
        if details:
            with st.expander("成分股详情", expanded=False):
                import pandas as pd

                rows = []
                for sym, d in details.items():
                    rows.append(
                        {
                            "代码": sym,
                            "名称": d.get("name", ""),
                            "现价": format_currency(d.get("current_price")),
                            "收益率": format_percent(d.get("total_return_pct")),
                            "市值": format_large_number(d.get("market_cap")),
                            "行业": d.get("sector", ""),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

else:
    # ─── 对比模式 ────────────────────────────────
    st.markdown("### 主题对比")

    theme_names = {t.get("theme_id"): t.get("name", t.get("theme_id", "")) for t in themes}
    theme_ids = list(theme_names.keys())

    selected_themes = st.multiselect(
        "选择要对比的主题（2-5 个）",
        theme_ids,
        format_func=lambda x: theme_names.get(x, x),
        max_selections=5,
        key="compare_themes",
    )

    if len(selected_themes) >= 2:
        with st.spinner("正在分析所选主题……"):
            results = {}
            for tid in selected_themes:
                results[tid] = analyze_theme(tid)

        # 对比指标
        st.markdown("#### 收益率对比")

        horizons = ["1w", "1m", "3m", "6m", "1y", "ytd"]
        horizon_labels = ["1 周", "1 月", "3 月", "6 月", "1 年", "YTD"]

        series_data = []
        colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444"]
        for i, tid in enumerate(selected_themes):
            r = results.get(tid, {})
            perf = r.get("theme_performance", {})
            values = []
            for h in horizons:
                val = perf.get(h, "0%")
                try:
                    values.append(float(str(val).replace("%", "").replace("+", "")))
                except ValueError:
                    values.append(0)
            series_data.append(
                {
                    "name": theme_names.get(tid, tid),
                    "values": values,
                    "color": colors[i % len(colors)],
                }
            )

        from components.plotly_charts import create_grouped_bar

        fig = create_grouped_bar(
            horizon_labels, series_data, title="不同周期收益率 (%)", height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # 健康度 & 动量
        st.markdown("#### 健康度 & 动量对比")
        categories = ["健康度", "动量", "分散度"]

        for i, tid in enumerate(selected_themes):
            r = results.get(tid, {})
            risk = r.get("theme_risk", {})
            div_score_str = risk.get("diversification_score", "Moderate")
            div_cn = {"Low": "偏低", "Moderate": "中等", "Good": "良好", "Excellent": "优秀"}.get(
                div_score_str, div_score_str
            )

            cols = st.columns(3)
            cols[0].metric(theme_names.get(tid, tid) + " · 健康度", r.get("theme_health_score", 0))
            cols[1].metric("动量得分", r.get("momentum_score", 0))
            cols[2].metric("分散度", div_cn)

    elif selected_themes:
        st.info("至少选择 2 个主题才能进行对比。")
