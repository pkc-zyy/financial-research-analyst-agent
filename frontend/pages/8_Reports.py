"""
研究报告 - 生成并下载投资研究报告。
"""

import json
from datetime import datetime

import streamlit as st
from components.header import render_header

from utils.data_service import (
    analyze_disruption,
    analyze_earnings,
    get_company_info,
    get_company_news,
    get_financial_health,
    get_stock_price,
    get_technical_analysis,
)
from utils.formatters import (
    format_currency,
    format_date,
    format_large_number,
    format_number,
    format_percent,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="研究报告 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 研究报告")
st.caption("一键生成并下载投资研究报告")

# ─── 报告配置 ────────────────────────────────────────────
c1, c2 = st.columns([2, 1])

with c1:
    symbols_input = st.text_input(
        "股票代码（英文逗号分隔）",
        value=st.session_state.get("selected_symbol", "AAPL"),
        placeholder="例如：AAPL, MSFT",
        key="report_symbols",
    )

with c2:
    report_format = st.selectbox("导出格式", ["Markdown", "JSON"], key="report_format")

symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

# 章节选择
st.markdown("**包含章节：**")
sections = st.columns(5)
include_overview = sections[0].checkbox("公司概览", value=True)
include_technical = sections[1].checkbox("技术面分析", value=True)
include_fundamental = sections[2].checkbox("基本面分析", value=True)
include_disruption = sections[3].checkbox("颠覆分析", value=False)
include_earnings = sections[4].checkbox("财报分析", value=False)

generate = st.button("生成报告", use_container_width=False)

if not generate:
    st.info("请在上方配置报告内容后点击「生成报告」。")
    st.stop()

if not symbols:
    st.warning("至少输入 1 个股票代码。")
    st.stop()

# ─── 生成报告 ─────────────────────────────────────────
with st.spinner(f"正在为 {', '.join(symbols)} 生成报告……"):
    report_data = {
        "title": "投资研究报告",
        "generated_at": datetime.utcnow().isoformat(),
        "symbols": symbols,
        "sections": {},
    }

    markdown_parts = [
        f"# 投资研究报告",
        f"**生成时间：** {datetime.utcnow().strftime('%Y 年 %m 月 %d 日 %H:%M UTC')}",
        f"**标的：** {', '.join(symbols)}",
        "",
        "---",
        "",
    ]

    for symbol in symbols:
        markdown_parts.append(f"## {symbol}")
        symbol_data = {}

        # 概览
        if include_overview:
            price = get_stock_price(symbol)
            company = get_company_info(symbol)

            if "error" not in price:
                symbol_data["overview"] = {
                    "name": company.get("name", symbol),
                    "sector": company.get("sector", "N/A"),
                    "industry": company.get("industry", "N/A"),
                    "price": price.get("current_price", 0),
                    "change_percent": price.get("change_percent", 0),
                    "market_cap": price.get("market_cap", 0),
                    "pe_ratio": price.get("pe_ratio"),
                    "eps": price.get("eps"),
                    "52_week_high": price.get("52_week_high"),
                    "52_week_low": price.get("52_week_low"),
                }

                markdown_parts.extend(
                    [
                        f"### 公司概览",
                        f"- **公司：** {company.get('name', symbol)}",
                        f"- **行业板块：** {company.get('sector', 'N/A')} / {company.get('industry', 'N/A')}",
                        f"- **现价：** {format_currency(price.get('current_price'))}（{format_percent(price.get('change_percent', 0))}）",
                        f"- **市值：** {format_large_number(price.get('market_cap'))}",
                        f"- **市盈率 P/E：** {format_number(price.get('pe_ratio'))}",
                        f"- **每股收益 EPS：** {format_currency(price.get('eps'))}",
                        f"- **52 周区间：** {format_currency(price.get('52_week_low'))} - {format_currency(price.get('52_week_high'))}",
                        "",
                    ]
                )

        # 技术面
        if include_technical:
            tech = get_technical_analysis(symbol)
            if "error" not in tech:
                rsi = tech.get("rsi", {})
                macd = tech.get("macd", {})
                ma = tech.get("moving_averages", {})

                symbol_data["technical"] = {
                    "rsi": rsi,
                    "macd": macd,
                    "moving_averages": ma,
                    "bollinger_bands": tech.get("bollinger_bands", {}),
                    "patterns": tech.get("patterns", {}),
                }

                # 信号逻辑
                rsi_val = rsi.get("value", 50)
                macd_hist = macd.get("histogram", 0) or 0
                if isinstance(rsi_val, (int, float)) and rsi_val < 30 and macd_hist > 0:
                    rec = "买入"
                elif isinstance(rsi_val, (int, float)) and rsi_val > 70 and macd_hist < 0:
                    rec = "卖出"
                else:
                    rec = "持有"

                signal = rsi.get("signal", "N/A")
                signal_cn = (
                    "超卖" if "OVERSOLD" in str(signal).upper()
                    else "超买" if "OVERBOUGHT" in str(signal).upper() else "中性"
                )
                trend_map = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}
                macd_trend_cn = trend_map.get(str(macd.get("trend", "N/A")).lower(), str(macd.get("trend", "N/A")).title())
                ma_trend_cn = trend_map.get(str(ma.get("trend", "N/A")).lower(), str(ma.get("trend", "N/A")).title())

                markdown_parts.extend(
                    [
                        f"### 技术面分析",
                        f"- **RSI (14)：** {format_number(rsi.get('value'))}（{signal_cn}）",
                        f"- **MACD 趋势：** {macd_trend_cn}",
                        f"- **MACD 柱状：** {format_number(macd.get('histogram'), 4)}",
                        f"- **均线趋势：** {ma_trend_cn}",
                        f"- **综合信号：** **{rec}**",
                        "",
                    ]
                )

                patterns = tech.get("patterns", {}).get("patterns_detected", [])
                if patterns:
                    markdown_parts.append("**识别到的形态：**")
                    for p in patterns:
                        impl = p.get("implication", "neutral")
                        impl_cn = (
                            "看涨" if "bullish" in str(impl).lower()
                            else "看跌" if "bearish" in str(impl).lower() else "中性"
                        )
                        markdown_parts.append(
                            f"- {p.get('name', '未知形态')}（{impl_cn}，置信度 {p.get('confidence', 0)*100:.0f}%）"
                        )
                    markdown_parts.append("")

        # 基本面
        if include_fundamental:
            health = get_financial_health(symbol)
            if "error" not in health:
                symbol_data["fundamental"] = health

                assessment = health.get("overall_assessment", "N/A")
                assess_cn = (
                    "强劲" if "strong" in str(assessment).lower()
                    else "偏弱" if "weak" in str(assessment).lower() else assessment
                )
                markdown_parts.extend(
                    [
                        f"### 基本面分析",
                        f"- **财务健康评分：** {format_number(health.get('health_score'))}/10",
                        f"- **整体评价：** {assess_cn}",
                        "",
                    ]
                )

                strengths = health.get("strengths", [])
                if strengths:
                    markdown_parts.append("**核心优势：**")
                    for s in strengths:
                        markdown_parts.append(f"- {s}")
                    markdown_parts.append("")

                weaknesses = health.get("weaknesses", [])
                if weaknesses:
                    markdown_parts.append("**风险因素：**")
                    for w in weaknesses:
                        markdown_parts.append(f"- {w}")
                    markdown_parts.append("")

        # 颠覆分析
        if include_disruption:
            disruption = analyze_disruption(symbol)
            if "error" not in disruption:
                cls = disruption.get("classification", "N/A")
                cls_cn_map = {
                    "Active Disruptor": "积极颠覆者",
                    "Moderate Innovator": "稳健创新者",
                    "Stable Incumbent": "在位稳健者",
                    "At Risk": "风险型企业",
                }
                cls_cn = cls_cn_map.get(cls, cls)
                symbol_data["disruption"] = {
                    "score": disruption.get("disruption_score"),
                    "classification": cls_cn,
                    "strengths": disruption.get("strengths", []),
                    "risk_factors": disruption.get("risk_factors", []),
                }

                markdown_parts.extend(
                    [
                        f"### 颠覆分析",
                        f"- **颠覆得分：** {disruption.get('disruption_score', 0)}/100",
                        f"- **分类：** {cls_cn}",
                        "",
                    ]
                )

        # 财报
        if include_earnings:
            earnings = analyze_earnings(symbol)
            if "error" not in earnings:
                surprise = earnings.get("earnings_surprise_history", {}).get("last_8_quarters", {})
                quality = earnings.get("earnings_quality", {})

                pattern = surprise.get("pattern", "N/A")
                pattern_cn = (
                    "持续超预期" if "consistent beat" in str(pattern).lower()
                    else "波动较大" if "volatile" in str(pattern).lower() or "mixed" in str(pattern).lower()
                    else "持续不及预期" if "miss" in str(pattern).lower()
                    else pattern
                )
                assess = quality.get("assessment", "N/A")
                assess_cn = (
                    "高质量" if "high" in str(assess).lower()
                    else "低质量" if "low" in str(assess).lower() else assess
                )

                symbol_data["earnings"] = {
                    "beat_rate": surprise.get("beat_rate"),
                    "average_surprise": surprise.get("average_surprise"),
                    "pattern": pattern_cn,
                    "quality_score": quality.get("score"),
                    "quality_assessment": assess_cn,
                }

                markdown_parts.extend(
                    [
                        f"### 财报分析",
                        f"- **超预期胜率：** {surprise.get('beat_rate', 'N/A')}",
                        f"- **平均超预期幅度：** {surprise.get('average_surprise', 'N/A')}",
                        f"- **规律：** {pattern_cn}",
                        f"- **财报质量：** {format_number(quality.get('score'))}/10（{assess_cn}）",
                        "",
                    ]
                )

        report_data["sections"][symbol] = symbol_data
        markdown_parts.extend(["", "---", ""])

    # 免责声明
    markdown_parts.extend(
        [
            "## 免责声明",
            "本报告仅供参考，不构成任何投资建议。投资者在做出决策前请自行研究并咨询专业顾问。",
            "",
            f"*由「智能金融 AI」研究平台生成 · {datetime.utcnow().strftime('%Y 年 %m 月 %d 日')}*",
        ]
    )

    markdown_content = "\n".join(markdown_parts)
    json_content = json.dumps(report_data, indent=2, default=str, ensure_ascii=False)

# ─── 报告预览 ──────────────────────────────────────────
st.markdown("---")
st.markdown("### 报告预览")

if report_format == "Markdown":
    st.markdown(markdown_content)
else:
    st.json(report_data)

# ─── 下载按钮 ────────────────────────────────────────
st.markdown("---")
st.markdown("### 下载报告")

c1, c2 = st.columns(2)

with c1:
    st.download_button(
        label="下载 Markdown",
        data=markdown_content,
        file_name=f"研究报告_{'_'.join(symbols)}_{datetime.utcnow().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        use_container_width=True,
    )

with c2:
    st.download_button(
        label="下载 JSON",
        data=json_content,
        file_name=f"研究报告_{'_'.join(symbols)}_{datetime.utcnow().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )
