"""
主题工具：自定义 CSS 注入、深色/浅色模式切换、设计常量（颜色/布局）。
"""

import os

import streamlit as st

# ── 配色面板 ───────────────────────────────────────────

DARK_COLORS = {
    "bg_base": "#09090b",
    "bg_primary": "#0c0c0f",
    "bg_secondary": "#131316",
    "bg_card": "#1c1c21",
    "bg_card_hover": "#222228",
    "text_primary": "#fafafa",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "accent_primary": "#6366f1",
    "accent_secondary": "#8b5cf6",
    "success": "#22c55e",
    "warning": "#eab308",
    "danger": "#ef4444",
    "border": "rgba(255, 255, 255, 0.08)",
    "border_light": "rgba(255, 255, 255, 0.06)",
}

LIGHT_COLORS = {
    "bg_base": "#f8f9fa",
    "bg_primary": "#ffffff",
    "bg_secondary": "#f1f3f5",
    "bg_card": "#ffffff",
    "bg_card_hover": "#f8f9fa",
    "text_primary": "#1a1a2e",
    "text_secondary": "#495057",
    "text_muted": "#868e96",
    "accent_primary": "#4f46e5",
    "accent_secondary": "#7c3aed",
    "success": "#16a34a",
    "warning": "#ca8a04",
    "danger": "#dc2626",
    "border": "rgba(0, 0, 0, 0.1)",
    "border_light": "rgba(0, 0, 0, 0.06)",
}


def _get_theme() -> str:
    """从会话状态读取当前主题模式（dark/light）。"""
    return st.session_state.get("theme_mode", "dark")


def get_colors() -> dict:
    """获取当前主题对应的配色字典。"""
    return LIGHT_COLORS if _get_theme() == "light" else DARK_COLORS


# 向后兼容别名 — 默认使用深色
COLORS = DARK_COLORS

# Plotly 图表模板
PLOTLY_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": COLORS["bg_secondary"],
    "font": {"color": COLORS["text_primary"], "family": "Inter, -apple-system, sans-serif"},
    "xaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
        "tickfont": {"color": COLORS["text_muted"]},
    },
    "yaxis": {
        "gridcolor": COLORS["border_light"],
        "zerolinecolor": COLORS["border"],
        "tickfont": {"color": COLORS["text_muted"]},
    },
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}


def inject_css():
    """向 Streamlit 应用注入自定义 CSS 主题。"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")

    css_content = ""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

    # 浅色模式 CSS 覆盖
    theme = _get_theme()
    if theme == "light":
        c = LIGHT_COLORS
        css_content += f"""
        /* 浅色模式覆盖 */
        .stApp, [data-testid="stAppViewContainer"] {{
            background-color: {c['bg_base']} !important;
            color: {c['text_primary']} !important;
        }}
        [data-testid="stSidebar"] {{
            background-color: {c['bg_primary']} !important;
        }}
        .stMarkdown, .stText, p, span, label, h1, h2, h3, h4, h5, h6 {{
            color: {c['text_primary']} !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {c['text_primary']} !important;
        }}
        """

    # 移动端响应式增强
    css_content += """
    /* 移动端响应式增强 */
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.5rem !important; }
        [data-testid="column"] { min-width: 100% !important; }
        .brand-logo .logo-text { font-size: 1rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
        [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
    }
    @media (max-width: 480px) {
        .block-container { padding: 0.5rem 0.25rem !important; }
        [data-testid="stTable"] { font-size: 0.75rem !important; }
    }
    """

    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)


def render_theme_toggle():
    """在侧边栏或顶栏渲染深色/浅色主题切换按钮。"""
    current = _get_theme()
    icon = "☀️" if current == "dark" else "🌙"
    label = "浅色模式" if current == "dark" else "深色模式"

    if st.button(f"{icon} {label}", key="theme_toggle", use_container_width=True):
        st.session_state.theme_mode = "light" if current == "dark" else "dark"
        st.rerun()


def get_plotly_layout(**overrides):
    """获取默认 Plotly 布局的副本，支持传入覆盖参数。

    对 xaxis、yaxis、margin、font 等字典字段做深合并，覆盖项在默认基础上增量更新，
    而不是整体替换。
    """
    import copy

    layout = copy.deepcopy(PLOTLY_LAYOUT)
    for key, value in overrides.items():
        if key in layout and isinstance(layout[key], dict) and isinstance(value, dict):
            layout[key].update(value)
        else:
            layout[key] = value
    return layout
