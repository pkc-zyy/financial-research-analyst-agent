"""
精简侧边栏组件 - 仅保留代码搜索与自选股功能。
品牌与导航已搬到顶部导航栏。
"""

import streamlit as st

from utils.session import add_to_watchlist, init_session_state


def render_sidebar():
    """渲染极简侧边栏：股票搜索 + 自选股列表。"""
    init_session_state()

    with st.sidebar:
        # 股票代码搜索
        st.markdown("### 股票代码")
        symbol = st.text_input(
            "股票代码",
            value=st.session_state.get("selected_symbol", ""),
            placeholder="例如: AAPL, MSFT",
            key="sidebar_symbol_input",
            label_visibility="collapsed",
        )
        if symbol:
            st.session_state.selected_symbol = symbol.upper().strip()

        st.markdown("---")

        # 自选股
        st.markdown("### 自选股")
        watchlist = st.session_state.get("watchlist", [])

        if watchlist:
            cols_per_row = 3
            for i in range(0, len(watchlist), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx < len(watchlist):
                        sym = watchlist[idx]
                        if col.button(sym, key=f"wl_{sym}", use_container_width=True):
                            st.session_state.selected_symbol = sym
                            st.rerun()
        else:
            st.caption("自选股列表为空。")

        # 加入自选股
        new_sym = st.text_input(
            "加入自选股",
            placeholder="输入代码添加",
            key="add_watchlist_input",
            label_visibility="collapsed",
        )
        if new_sym:
            add_to_watchlist(new_sym)
            st.rerun()

        st.markdown("---")

        # 页脚信息
        st.markdown(
            "<div style='font-size: 0.65rem; color: #6b7280; line-height: 1.4;'>"
            "数据来源：雅虎财经 (Yahoo Finance)"
            "</div>",
            unsafe_allow_html=True,
        )
