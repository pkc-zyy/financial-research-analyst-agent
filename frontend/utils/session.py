"""
会话状态管理工具（Streamlit session state）。
"""

import streamlit as st


def init_session_state():
    """为所有用到的会话状态字段设置合理默认值。"""
    defaults = {
        "selected_symbol": "",
        "watchlist": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        "portfolio_symbols": [],
        "portfolio_weights": {},
        "selected_theme": None,
        "comparison_symbols": [],
        "analysis_period": "1y",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def update_symbol(symbol: str):
    """更新全局选中的股票代码。"""
    st.session_state.selected_symbol = symbol.upper().strip()


def add_to_watchlist(symbol: str):
    """把一只股票加入自选股列表。"""
    symbol = symbol.upper().strip()
    if symbol and symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(symbol)


def remove_from_watchlist(symbol: str):
    """把一只股票从自选股列表移除。"""
    st.session_state.watchlist = [
        s for s in st.session_state.watchlist if s != symbol.upper().strip()
    ]


def get_symbol():
    """获取当前选中的股票代码。"""
    return st.session_state.get("selected_symbol", "")
