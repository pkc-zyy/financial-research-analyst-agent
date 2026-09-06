"""
顶部导航栏 - 品牌标识与菜单在同一行展示。
"""

import streamlit as st

from components.llm_settings import render_llm_settings

# 导航结构（分组）
NAV_GROUPS = {
    "分析中心": [
        ("总览仪表盘", "pages/1_Dashboard.py", "📊"),
        ("个股分析", "pages/2_Stock_Analysis.py", "📈"),
        ("同业对比", "pages/4_Peer_Comparison.py", "⚖️"),
        ("业绩走势", "pages/10_Performance.py", "🎯"),
        ("市场情绪", "pages/11_Sentiment.py", "💬"),
    ],
    "深度研究": [
        ("主题投资", "pages/3_Thematic_Investing.py", "🎨"),
        ("颠覆创新", "pages/5_Market_Disruption.py", "🚀"),
        ("季度财报", "pages/6_Quarterly_Earnings.py", "📑"),
        ("做空情报", "pages/14_Short_Interest.py", "📉"),
        ("分析师共识", "pages/16_Analyst_Consensus.py", "🎯"),
    ],
    "投资组合": [
        ("组合分析", "pages/7_Portfolio_Analysis.py", "💼"),
        ("股息分红", "pages/15_Dividends.py", "💰"),
        ("研报导出", "pages/8_Reports.py", "📄"),
        ("智能告警", "pages/17_Alerts.py", "🔔"),
    ],
    "数据资讯": [
        ("新闻中心", "pages/9_News.py", "📰"),
        ("ETF 筛选器", "pages/12_ETF_Screener.py", "🔍"),
        ("宏观经济", "pages/13_Macro_Economy.py", "🌐"),
    ],
}

GROUP_ICONS = {
    "分析中心": "📊",
    "深度研究": "🔬",
    "投资组合": "💼",
    "数据资讯": "📰",
}


def render_header():
    """渲染顶部导航栏（品牌 + 菜单 + 模型设置）。"""

    # 为包含 brand-logo 的容器注入 sticky 样式
    st.markdown(
        """
        <style>
            /* 仅针对含有品牌 logo 的容器启用吸顶 */
            [data-testid="stMainBlockContainer"] > div > div:has(.brand-logo) {
                position: sticky !important;
                top: 0 !important;
                z-index: 999 !important;
                background: #09090b !important;
                padding: 0.5rem 0 0.25rem 0 !important;
                margin: 0 -1rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 单排布局：Logo | 四个分组 | 模型设置
    cols = st.columns([2.4, 1, 1, 1, 1, 0.6])

    # 现代 Logo / 品牌
    with cols[0]:
        st.markdown(
            """
            <a href="/" target="_self" style="text-decoration: none;">
                <div class="brand-logo">
                    <div class="logo-icon">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 17L9 11L13 15L21 7" stroke="url(#grad1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M17 7H21V11" stroke="url(#grad1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                            <circle cx="12" cy="19" r="2" fill="url(#grad1)" opacity="0.6"/>
                            <circle cx="6" cy="19" r="1.5" fill="url(#grad1)" opacity="0.4"/>
                            <circle cx="18" cy="19" r="1.5" fill="url(#grad1)" opacity="0.4"/>
                            <defs>
                                <linearGradient id="grad1" x1="3" y1="7" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                                    <stop stop-color="#818cf8"/>
                                    <stop offset="1" stop-color="#6366f1"/>
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <span class="logo-text">
                        <span class="logo-finance">智能金融</span><span class="logo-ai">AI</span>
                    </span>
                </div>
            </a>
            <style>
                .brand-logo {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    height: 38px;
                    transition: all 0.2s ease;
                }
                .brand-logo:hover {
                    opacity: 0.85;
                }
                .logo-icon {
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .logo-icon svg {
                    width: 100%;
                    height: 100%;
                }
                .logo-text {
                    font-family: 'Inter', -apple-system, sans-serif;
                    font-size: 1.25rem;
                    font-weight: 700;
                    letter-spacing: -0.03em;
                }
                .logo-finance {
                    color: #fafafa;
                }
                .logo-ai {
                    background: linear-gradient(135deg, #818cf8, #6366f1);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # 导航下拉菜单
    for idx, (group_name, pages) in enumerate(NAV_GROUPS.items()):
        with cols[idx + 1]:
            icon = GROUP_ICONS.get(group_name, "📁")
            with st.popover(f"{icon} {group_name}", use_container_width=True):
                for page_name, page_path, page_icon in pages:
                    if st.button(
                        f"{page_icon}  {page_name}",
                        key=f"nav_{page_path}",
                        use_container_width=True,
                    ):
                        st.switch_page(page_path)

    # 模型 / API Key 设置 — 所有页面均可访问
    with cols[5]:
        render_llm_settings()

    # 主题切换
    from utils.theme import render_theme_toggle

    with st.container():
        c1, c2 = st.columns([10, 1])
        with c2:
            render_theme_toggle()

    # 分隔线
    st.markdown(
        "<div style='height: 1px; background: linear-gradient(90deg, rgba(99,102,241,0.3), transparent); margin: 0.35rem 0 0.5rem;'></div>",
        unsafe_allow_html=True,
    )
