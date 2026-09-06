"""
投资组合分析 - 多股票组合的相关性与行业配置分析。
"""

import numpy as np
import pandas as pd
import streamlit as st
from components.charts import render_area_chart
from components.header import render_header
from components.plotly_charts import (
    create_donut_chart,
    create_gauge_chart,
    create_heatmap,
)

from utils.data_service import (
    get_company_info,
    get_correlation_analysis,
    get_efficient_frontier,
    get_historical_data,
    get_portfolio_benchmark,
    get_rebalance_suggestions,
    get_stock_price,
    get_technical_analysis,
    optimize_portfolio,
)
from utils.formatters import format_currency, format_large_number, format_percent
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="投资组合 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 投资组合分析")
st.caption("对多只股票构成的组合进行相关性与配置洞察")

# ─── 组合构建器 ───────────────────────────────────────
symbols_input = st.text_input(
    "组合股票代码（英文逗号分隔）",
    value=", ".join(st.session_state.get("portfolio_symbols", []))
    or "AAPL, MSFT, GOOGL, AMZN, NVDA",
    placeholder="例如：AAPL, MSFT, GOOGL, AMZN, NVDA",
    key="portfolio_input",
)

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
st.session_state.portfolio_symbols = symbols

if len(symbols) < 2:
    st.info("至少输入 2 个以英文逗号分隔的股票代码。")
    st.stop()

analyze = st.button("分析投资组合", use_container_width=False)

if analyze or symbols:
    with st.spinner(f"正在分析由 {len(symbols)} 只股票构成的投资组合……"):
        # 获取所有股票数据
        stock_data = {}
        hist_data = {}
        company_data = {}

        for sym in symbols:
            stock_data[sym] = get_stock_price(sym)
            hist_data[sym] = get_historical_data(sym, "1y")
            company_data[sym] = get_company_info(sym)

    # 过滤掉获取失败的股票
    valid_symbols = [s for s in symbols if "error" not in stock_data.get(s, {"error": True})]
    errored = [s for s in symbols if s not in valid_symbols]

    if errored:
        st.warning(f"无法获取以下股票的数据：{', '.join(errored)}")

    if len(valid_symbols) < 2:
        st.error("至少需要 2 只可正常获取的股票才能进行投资组合分析。")
        st.stop()

    # ─── 组合概览 ──────────────────────────────────
    st.markdown("---")
    st.markdown("### 组合概览")

    total_mcap = sum(stock_data[s].get("market_cap", 0) or 0 for s in valid_symbols)

    c1, c2, c3 = st.columns(3)
    c1.metric("股票数量", len(valid_symbols))
    c2.metric("总市值", format_large_number(total_mcap))
    c3.metric("权重方式", "等权重")

    # ─── 每只股票汇总表 ─────────────────────────────
    st.markdown("### 个股明细")

    rows = []
    for sym in valid_symbols:
        sd = stock_data[sym]
        cd = company_data.get(sym, {})
        rows.append(
            {
                "代码": sym,
                "名称": cd.get("name", sym),
                "现价": format_currency(sd.get("current_price")),
                "涨跌幅 %": format_percent(sd.get("change_percent", 0)),
                "市值": format_large_number(sd.get("market_cap")),
                "市盈率 P/E": f"{sd.get('pe_ratio', 0):.1f}" if sd.get("pe_ratio") else "--",
                "行业": cd.get("sector", "--"),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ─── 行业配置 ───────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### 行业分布")
        sectors = {}
        for sym in valid_symbols:
            sector = company_data.get(sym, {}).get("sector", "未知")
            sectors[sector] = sectors.get(sector, 0) + 1

        if sectors:
            fig = create_donut_chart(
                labels=list(sectors.keys()),
                values=list(sectors.values()),
                title="行业构成",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("### 市值分布")
        cap_buckets_cn = {
            "超大盘 (>2000 亿美元)": 0,
            "大盘 (100-2000 亿美元)": 0,
            "中盘 (20-100 亿美元)": 0,
            "小盘 (<20 亿美元)": 0,
        }
        cap_buckets = {
            "Mega (>$200B)": "超大盘 (>2000 亿美元)",
            "Large ($10-200B)": "大盘 (100-2000 亿美元)",
            "Mid ($2-10B)": "中盘 (20-100 亿美元)",
            "Small (<$2B)": "小盘 (<20 亿美元)",
        }
        counts = {k: 0 for k in cap_buckets_cn.keys()}
        for sym in valid_symbols:
            mcap = stock_data[sym].get("market_cap", 0) or 0
            if mcap >= 200e9:
                counts["超大盘 (>2000 亿美元)"] += 1
            elif mcap >= 10e9:
                counts["大盘 (100-2000 亿美元)"] += 1
            elif mcap >= 2e9:
                counts["中盘 (20-100 亿美元)"] += 1
            else:
                counts["小盘 (<20 亿美元)"] += 1

        non_zero = {k: v for k, v in counts.items() if v > 0}
        if non_zero:
            fig = create_donut_chart(
                labels=list(non_zero.keys()),
                values=list(non_zero.values()),
                title="市值层级",
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ─── 小卡片 ────────────────────────────────────
    st.markdown("### 快捷信号")

    card_cols = st.columns(min(len(valid_symbols), 4))
    for i, sym in enumerate(valid_symbols):
        with card_cols[i % len(card_cols)]:
            sd = stock_data[sym]
            price = sd.get("current_price", 0)
            change = sd.get("change_percent", 0)
            change_color = "#10b981" if change >= 0 else "#ef4444"
            change_sign = "+" if change >= 0 else ""

            # 快速 RSI
            tech = get_technical_analysis(sym)
            rsi_val = "--"
            rsi_signal = "中性"
            if "error" not in tech:
                rsi = tech.get("rsi", {})
                rsi_val = (
                    f"{rsi.get('value', 0):.0f}"
                    if isinstance(rsi.get("value"), (int, float))
                    else "--"
                )
                signal = rsi.get("signal", "NEUTRAL")
                rsi_signal = (
                    "超卖" if "OVERSOLD" in str(signal).upper()
                    else "超买" if "OVERBOUGHT" in str(signal).upper() else "中性"
                )

            st.markdown(
                f"""
                <div class="card" style="text-align: center; padding: 1rem;">
                    <div style="font-weight: 800; font-size: 1.1rem; font-family: JetBrains Mono;">{sym}</div>
                    <div style="font-size: 1.3rem; font-weight: 700; font-family: JetBrains Mono; margin: 0.25rem 0;">
                        {format_currency(price)}
                    </div>
                    <div style="color: {change_color}; font-family: JetBrains Mono; font-size: 0.85rem;">
                        {change_sign}{change:.2f}%
                    </div>
                    <div style="margin-top: 0.5rem; font-size: 0.75rem; color: #9ca3af;">
                        RSI: {rsi_val} ({rsi_signal})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # ─── 相关性矩阵 ──────────────────────────────────
    st.markdown("### 相关性矩阵")

    # 构造对齐的收益率
    all_returns = {}
    min_len = float("inf")

    for sym in valid_symbols:
        hd = hist_data.get(sym, {})
        returns = hd.get("returns", [])
        if returns:
            all_returns[sym] = returns
            min_len = min(min_len, len(returns))

    if len(all_returns) >= 2 and min_len > 10:
        # 对齐到相同长度
        aligned = {sym: ret[: int(min_len)] for sym, ret in all_returns.items()}
        syms_list = list(aligned.keys())
        returns_matrix = np.array([aligned[s] for s in syms_list])

        corr_matrix = np.corrcoef(returns_matrix)

        fig = create_heatmap(
            matrix=corr_matrix.tolist(),
            x_labels=syms_list,
            y_labels=syms_list,
            title="收益率相关性矩阵",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 组合风险指标
        avg_corr = (corr_matrix.sum() - len(syms_list)) / (len(syms_list) * (len(syms_list) - 1))
        st.caption(f"平均两两相关系数：**{avg_corr:.3f}**")

        if avg_corr < 0.3:
            st.success(
                "分散效果良好 —— 组合各成分间平均相关性较低。"
            )
        elif avg_corr < 0.6:
            st.info("分散程度中等 —— 组合成分间存在一定相关性。")
        else:
            st.warning(
                "组合成分间相关性偏高，建议进一步分散投资。"
            )
    else:
        st.caption("收益率数据不足，暂无法计算相关性矩阵。")

    # ─── 组合风险指标 ──────────────────────────────
    st.markdown("---")
    st.markdown("### 组合风险指标（等权重）")

    if len(all_returns) >= 2 and min_len > 10:
        # 等权重组合收益率
        aligned_arr = np.array(
            [all_returns[s][: int(min_len)] for s in valid_symbols if s in all_returns]
        )
        portfolio_returns = np.mean(aligned_arr, axis=0)

        port_vol_daily = np.std(portfolio_returns)
        port_vol_annual = port_vol_daily * np.sqrt(252)
        port_mean_return = np.mean(portfolio_returns) * 252
        sharpe = (port_mean_return - 0.05) / port_vol_annual if port_vol_annual > 0 else 0

        # 最大回撤
        cumulative = np.cumprod(1 + portfolio_returns)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative) / peak
        max_dd = np.max(drawdown)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("年化波动率", format_percent(port_vol_annual * 100))
        c2.metric("预期收益率", format_percent(port_mean_return * 100))
        c3.metric("夏普比率", f"{sharpe:.2f}")
        c4.metric("最大回撤", format_percent(-max_dd * 100))

    # ─── 组合优化 (马科维茨) ────────────────
    st.markdown("---")
    st.markdown("### 组合优化")
    st.caption("基于现代投资组合理论（马科维茨）优化配置")

    opt_method = st.selectbox(
        "优化目标",
        options=["max_sharpe", "min_volatility", "risk_parity"],
        format_func=lambda x: {
            "max_sharpe": "最大化夏普比率（最佳风险调整后收益）",
            "min_volatility": "最小化波动率（最低风险）",
            "risk_parity": "风险平价（等风险贡献）",
        }.get(x, x),
        key="opt_method",
    )

    if st.button("开始优化", type="primary", key="optimize_btn"):
        syms_tuple = tuple(valid_symbols)

        with st.spinner("正在运行组合优化……"):
            opt_result = optimize_portfolio(syms_tuple, method=opt_method)

        if "error" in opt_result:
            st.error(opt_result["error"])
        else:
            # 优化后权重 vs 当前（等权重）
            alloc = opt_result.get("allocation", {})
            opt_metrics = opt_result.get("portfolio_metrics", {})

            ocol1, ocol2 = st.columns(2)

            with ocol1:
                st.markdown("**优化后配置**")
                alloc_rows = []
                for sym, data in alloc.items():
                    eq_w = round(100 / len(valid_symbols), 1)
                    opt_w = data.get("weight_pct", 0)
                    change = round(opt_w - eq_w, 1)
                    alloc_rows.append(
                        {
                            "代码": sym,
                            "当前 (%)": eq_w,
                            "最优 (%)": opt_w,
                            "变化": f"{change:+.1f}%",
                        }
                    )
                st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True, hide_index=True)

            with ocol2:
                st.markdown("**优化后指标**")
                st.metric("预期收益率", f"{opt_metrics.get('expected_return_pct', 0):.2f}%")
                st.metric("波动率", f"{opt_metrics.get('volatility_pct', 0):.2f}%")
                st.metric("夏普比率", f"{opt_metrics.get('sharpe_ratio', 0):.3f}")

            # 有效前沿
            st.markdown("---")
            st.markdown("**有效前沿**")
            with st.spinner("正在计算有效前沿……"):
                frontier = get_efficient_frontier(syms_tuple)

            if "error" not in frontier and frontier.get("frontier"):
                f_data = frontier["frontier"]
                f_df = pd.DataFrame(
                    [
                        {"风险 (%)": p["volatility_pct"], "收益率 (%)": p["return_pct"]}
                        for p in f_data
                    ]
                )
                st.scatter_chart(f_df, x="风险 (%)", y="收益率 (%)", color=None)

                # 标记特殊组合
                for p in f_data:
                    label = p.get("label")
                    if label:
                        st.caption(
                            f"**{label}**：收益率 {p['return_pct']}%，风险 {p['volatility_pct']}%，夏普比率 {p['sharpe']:.3f}"
                        )

            # 相关性洞察
            st.markdown("---")
            st.markdown("**相关性洞察**")
            with st.spinner("正在分析相关性……"):
                corr_result = get_correlation_analysis(syms_tuple)

            if "error" not in corr_result:
                insights = corr_result.get("insights", [])
                rating = corr_result.get("diversification_rating", "N/A")
                avg = corr_result.get("average_correlation", 0)

                st.markdown(f"**分散评级：** {rating}（平均相关系数 {avg:.3f}）")
                for insight in insights:
                    st.markdown(f"- {insight}")

            # 基准对比
            st.markdown("---")
            st.markdown("**对比标普 500 基准**")
            eq_weights = tuple([1 / len(valid_symbols)] * len(valid_symbols))
            with st.spinner("正在与基准进行对比……"):
                bench = get_portfolio_benchmark(syms_tuple, eq_weights)

            if "error" not in bench:
                rel = bench.get("relative_metrics", {})
                bcol1, bcol2, bcol3, bcol4 = st.columns(4)
                bcol1.metric("Alpha", f"{rel.get('alpha_pct', 0):+.2f}%")
                bcol2.metric("Beta", f"{rel.get('beta', 0):.3f}")
                bcol3.metric("跟踪误差", f"{rel.get('tracking_error_pct', 0):.2f}%")
                bcol4.metric("信息比率", f"{rel.get('information_ratio', 0):.3f}")

                interp = bench.get("interpretation", {})
                st.caption(f"Alpha 解读：{interp.get('alpha', '')} ｜ Beta 解读：{interp.get('beta', '')}")
