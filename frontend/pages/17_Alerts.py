"""
价格提醒中心 - 创建、编辑、管理价格触发提醒，
支持多通道通知方式、模拟触发历史，以及快捷提醒向导。
"""

import json
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
from components.header import render_header
from components.plotly_charts import create_line_chart

from utils.data_service import get_stock_price
from utils.formatters import format_currency, format_date, format_percent
from utils.session import init_session_state
from utils.theme import COLORS, inject_css


def get_current_prices(symbols):
    """按代码列表批量取当前价（返回 {symbol: price}），获取失败时回退 None。"""
    result = {}
    for s in symbols:
        try:
            d = get_stock_price(s)
            result[s] = d.get("current_price") or d.get("price")
        except Exception:
            result[s] = None
    return result

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="价格提醒 | 智能金融 AI",
    page_icon=":bell:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 价格提醒中心")
st.caption("创建自定义价格提醒，支持多种触发条件与通知渠道")

# ─── 映射字典 ──────────────────────────────────────────
CONDITION_CN = {
    "price_above": "价格高于",
    "price_below": "价格低于",
    "percent_change_up": "一日涨幅超过",
    "percent_change_down": "一日跌幅超过",
    "pct_from_52w_high": "距 52 周高点",
    "pct_from_52w_low": "距 52 周低点",
}
STATUS_CN = {
    "active": "启用中",
    "paused": "已暂停",
    "triggered": "已触发",
}
CHANNEL_CN = {
    "in_app": "站内提醒",
    "email": "邮件",
    "sms": "短信",
    "webhook": "Webhook",
}
PRIORITY_CN = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "critical": "紧急",
}
FREQUENCY_CN = {
    "once": "触发一次后停止",
    "daily": "每日最多一次",
    "realtime": "实时（每次满足都触发）",
}


# ─── 会话中提醒列表 ─────────────────────────────────────────

DEFAULT_ALERTS = [
    {
        "id": "demo_1",
        "symbol": "AAPL",
        "name": "Apple 跌破 180 美元",
        "condition": "price_below",
        "target": 180.0,
        "current": 212.49,
        "channel": "in_app",
        "frequency": "once",
        "priority": "high",
        "status": "active",
        "created_at": "2026-08-20 10:22",
        "last_triggered": None,
        "trigger_count": 0,
        "notes": "逢低加仓提醒",
    },
    {
        "id": "demo_2",
        "symbol": "TSLA",
        "name": "Tesla 大涨 5%",
        "condition": "percent_change_up",
        "target": 5.0,
        "current": 218.50,
        "channel": "in_app",
        "frequency": "daily",
        "priority": "medium",
        "status": "active",
        "created_at": "2026-08-22 14:06",
        "last_triggered": "2026-08-28 09:35",
        "trigger_count": 2,
        "notes": "",
    },
    {
        "id": "demo_3",
        "symbol": "NVDA",
        "name": "NVDA 突破 1400",
        "condition": "price_above",
        "target": 1400.0,
        "current": 1298.33,
        "channel": "email",
        "frequency": "once",
        "priority": "critical",
        "status": "active",
        "created_at": "2026-08-15 08:12",
        "last_triggered": None,
        "trigger_count": 0,
        "notes": "波段减仓",
    },
]

if "alerts_list" not in st.session_state:
    st.session_state.alerts_list = list(DEFAULT_ALERTS)

if "alert_history" not in st.session_state:
    st.session_state.alert_history = [
        {
            "time": "2026-08-28 09:35",
            "alert": "TSLA 大涨 5%",
            "symbol": "TSLA",
            "condition": "percent_change_up",
            "value_triggered": "+5.4%",
            "channel": "站内提醒",
            "notified": True,
        },
        {
            "time": "2026-08-24 15:41",
            "alert": "TSLA 大涨 5%",
            "symbol": "TSLA",
            "condition": "percent_change_up",
            "value_triggered": "+5.1%",
            "channel": "站内提醒",
            "notified": True,
        },
    ]


# ─── 工具函数 ──────────────────────────────────────────


def _status_badge(status: str) -> str:
    mapping = {
        "active": ("rgba(34,197,94,0.15)", "#22c55e", STATUS_CN.get(status, status)),
        "paused": ("rgba(161,161,170,0.15)", "#a1a1aa", STATUS_CN.get(status, status)),
        "triggered": ("rgba(239,68,68,0.15)", "#ef4444", STATUS_CN.get(status, status)),
    }
    bg, color, txt = mapping.get(status, ("rgba(99,102,241,0.1)", "#6366f1", status))
    return (
        f'<span style="display:inline-block;font-size:0.65rem;font-weight:600;'
        f"padding:0.15rem 0.55rem;border-radius:999px;background:{bg};"
        f'color:{color};border:1px solid {color}20;">{txt}</span>'
    )


def _priority_badge(priority: str) -> str:
    mapping = {
        "low": ("rgba(59,130,246,0.15)", "#3b82f6"),
        "medium": ("rgba(234,179,8,0.15)", "#eab308"),
        "high": ("rgba(249,115,22,0.15)", "#f97316"),
        "critical": ("rgba(239,68,68,0.15)", "#ef4444"),
    }
    bg, color = mapping.get(priority, ("rgba(99,102,241,0.1)", "#6366f1"))
    return (
        f'<span style="display:inline-block;font-size:0.65rem;font-weight:600;'
        f"padding:0.15rem 0.55rem;border-radius:999px;background:{bg};"
        f'color:{color};border:1px solid {color}20;">{PRIORITY_CN.get(priority, priority)}</span>'
    )


def _format_trigger(alert: dict) -> str:
    sym = alert.get("symbol", "")
    cond = alert.get("condition", "")
    tgt = alert.get("target", "--")
    cond_cn = CONDITION_CN.get(cond, cond)
    if cond.startswith("percent") or cond.startswith("pct_from"):
        return f"{sym} {cond_cn} {tgt}%"
    return f"{sym} {cond_cn} ${tgt}"


# ─── 概览 KPI ────────────────────────────────────────
alerts = st.session_state.get("alerts_list", [])
active_count = sum(1 for a in alerts if a.get("status") == "active")
paused_count = sum(1 for a in alerts if a.get("status") == "paused")
triggered_count = sum(1 for a in alerts if a.get("status") == "triggered")
critical_count = sum(1 for a in alerts if a.get("priority") == "critical" and a.get("status") == "active")

k1, k2, k3, k4 = st.columns(4)
k1.metric("提醒总数", len(alerts))
k2.metric("启用中", active_count)
k3.metric("已暂停", paused_count)
k4.metric("紧急级提醒", critical_count)

st.markdown("---")

# ─── 标签页 ────────────────────────────────────────

tab_create, tab_list, tab_history = st.tabs(["新建提醒", "全部提醒", "触发记录"])

# ─── Tab 1: 新建提醒 ──────────────────────────────────
with tab_create:
    st.markdown("### 创建新提醒")

    with st.form("alert_form", clear_on_submit=False, border=False):
        fc1, fc2 = st.columns(2)
        with fc1:
            symbol = st.text_input("股票代码", value="AAPL", placeholder="如 AAPL, TSLA")
            name = st.text_input("提醒名称", placeholder="例如：AAPL 跌破 180 美元")
            condition = st.selectbox(
                "触发条件",
                list(CONDITION_CN.keys()),
                format_func=lambda x: CONDITION_CN.get(x, x),
                index=1,
            )
            target = st.number_input(
                "阈值（价格或百分比）",
                min_value=0.0,
                step=1.0,
                value=180.0,
                format="%.2f",
            )
        with fc2:
            priority = st.selectbox(
                "优先级",
                list(PRIORITY_CN.keys()),
                format_func=lambda x: f"{PRIORITY_CN.get(x, x)} 优先级",
                index=2,
            )
            channel = st.selectbox(
                "通知渠道",
                list(CHANNEL_CN.keys()),
                format_func=lambda x: CHANNEL_CN.get(x, x),
                index=0,
            )
            frequency = st.selectbox(
                "触发频率",
                list(FREQUENCY_CN.keys()),
                format_func=lambda x: FREQUENCY_CN.get(x, x),
                index=0,
            )
            notes = st.text_input("备注（可选）", placeholder="例如：逢低加仓信号")

        submitted = st.form_submit_button("保存提醒", type="primary", use_container_width=True)

    if submitted:
        sym_clean = symbol.strip().upper()
        if not sym_clean:
            st.error("请输入股票代码。")
        else:
            current_price = None
            try:
                prices = get_current_prices([sym_clean]) or {}
                current_price = prices.get(sym_clean, target)
            except Exception:
                current_price = target

            new_name = (
                name.strip()
                or f"{sym_clean} {CONDITION_CN.get(condition, condition)} {target}"
            )

            new_alert = {
                "id": str(uuid.uuid4())[:8],
                "symbol": sym_clean,
                "name": new_name,
                "condition": condition,
                "target": target,
                "current": current_price,
                "channel": channel,
                "frequency": frequency,
                "priority": priority,
                "status": "active",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "last_triggered": None,
                "trigger_count": 0,
                "notes": notes,
            }
            st.session_state.alerts_list.insert(0, new_alert)
            st.success(f"已创建提醒：「{new_name}」，当前 {sym_clean} 价格 {current_price}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 快捷模板 ──
    st.markdown("### 快捷创建向导")
    quick_cols = st.columns(4)
    with quick_cols[0]:
        if st.button("📉 52 周高点回落 10%", use_container_width=True):
            st.session_state.quick_tpl = {
                "condition": "pct_from_52w_high",
                "target": 10.0,
                "priority": "medium",
            }
            st.info("模板已载入，调整表单后点「保存提醒」")
    with quick_cols[1]:
        if st.button("🔥 突破 200 日均线", use_container_width=True):
            st.session_state.quick_tpl = {
                "condition": "price_above",
                "target": 190.0,
                "priority": "high",
            }
            st.info("模板已载入，请设置实际目标价位")
    with quick_cols[2]:
        if st.button("🛡️ 止损 -5%", use_container_width=True):
            st.session_state.quick_tpl = {
                "condition": "percent_change_down",
                "target": 5.0,
                "priority": "critical",
            }
            st.info("模板已载入，调整表单后点「保存提醒」")
    with quick_cols[3]:
        if st.button("🚀 单日反弹 +7%", use_container_width=True):
            st.session_state.quick_tpl = {
                "condition": "percent_change_up",
                "target": 7.0,
                "priority": "high",
            }
            st.info("模板已载入，调整表单后点「保存提醒」")

# ─── Tab 2: 全部提醒 ─────────────────────────────────
with tab_list:
    if not alerts:
        st.info("暂无提醒，请在「新建提醒」中创建。")
    else:
        st.markdown("### 我的提醒")

        # 过滤控制
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            filt_status = st.multiselect(
                "按状态过滤",
                options=list(STATUS_CN.keys()),
                default=list(STATUS_CN.keys()),
                format_func=lambda x: STATUS_CN.get(x, x),
            )
        with fc2:
            filt_priority = st.multiselect(
                "按优先级过滤",
                options=list(PRIORITY_CN.keys()),
                default=list(PRIORITY_CN.keys()),
                format_func=lambda x: PRIORITY_CN.get(x, x),
            )
        with fc3:
            filt_symbol = st.text_input("按代码过滤", placeholder="例如 AAPL")

        alerts_df = pd.DataFrame(alerts)
        if filt_status:
            alerts_df = alerts_df[alerts_df["status"].isin(filt_status)]
        if filt_priority:
            alerts_df = alerts_df[alerts_df["priority"].isin(filt_priority)]
        if filt_symbol:
            alerts_df = alerts_df[
                alerts_df["symbol"].str.contains(filt_symbol.strip().upper())
            ]

        if alerts_df.empty:
            st.caption("当前筛选条件下没有匹配的提醒。")
        else:
            # 行级操作
            for _, a in alerts_df.iterrows():
                aid = a["id"]
                sym = a["symbol"]
                current = a.get("current", 0)
                status = a["status"]
                with st.container():
                    lcol, rcol = st.columns([5, 1])
                    with lcol:
                        st.markdown(
                            f"""
                            <div style="padding: 0.75rem 1rem; background: {COLORS.get('bg_card', '#1f1f23')};
                                        border-radius: 10px; border: 1px solid {COLORS.get('border', '#27272a')};">
                                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                                    {_status_badge(status)}
                                    {_priority_badge(a['priority'])}
                                    <span style="font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: {COLORS.get('text_primary', '#fafafa')};">{sym}</span>
                                    <span style="color: {COLORS.get('text_muted', '#71717a')}; font-size: 0.75rem;">#{aid}</span>
                                </div>
                                <div style="font-size: 0.9rem; font-weight: 500; color: {COLORS.get('text_primary', '#fafafa')}; margin: 0.25rem 0;">{a['name']}</div>
                                <div style="font-size: 0.78rem; color: {COLORS.get('text_secondary', '#a1a1aa')};">
                                    {_format_trigger(a.to_dict())} · 当前 {format_currency(current)} ·
                                    通知：{CHANNEL_CN.get(a['channel'], a['channel'])} ·
                                    频率：{FREQUENCY_CN.get(a['frequency'], a['frequency'])}
                                </div>
                                {f"<div style='font-size: 0.7rem; color: {COLORS.get('text_muted', '#71717a')}; margin-top: 0.25rem;'>📝 {a['notes']}</div>" if a.get('notes') else ""}
                                <div style="font-size: 0.65rem; color: {COLORS.get('text_muted', '#71717a')}; margin-top: 0.3rem;">
                                    创建：{a['created_at']} ·
                                    最近触发：{a['last_triggered'] or '从未'} ·
                                    累计触发：{a.get('trigger_count', 0)} 次
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with rcol:
                        if status == "active":
                            if st.button("⏸ 暂停", key=f"pause_{aid}", use_container_width=True):
                                for i, al in enumerate(st.session_state.alerts_list):
                                    if al["id"] == aid:
                                        st.session_state.alerts_list[i]["status"] = "paused"
                                        st.rerun()
                        else:
                            if st.button("▶️ 启用", key=f"resume_{aid}", use_container_width=True):
                                for i, al in enumerate(st.session_state.alerts_list):
                                    if al["id"] == aid:
                                        st.session_state.alerts_list[i]["status"] = "active"
                                        st.rerun()
                        st.write("")
                        if st.button("🗑 删除", key=f"delete_{aid}", use_container_width=True):
                            st.session_state.alerts_list = [
                                al for al in st.session_state.alerts_list if al["id"] != aid
                            ]
                            st.rerun()

        # 批量操作
        st.markdown("<br>", unsafe_allow_html=True)
        batch_cols = st.columns(4)
        with batch_cols[0]:
            if st.button("全部启用", use_container_width=True):
                for a in st.session_state.alerts_list:
                    a["status"] = "active"
                st.rerun()
        with batch_cols[1]:
            if st.button("全部暂停", use_container_width=True):
                for a in st.session_state.alerts_list:
                    a["status"] = "paused"
                st.rerun()
        with batch_cols[2]:
            json_data = json.dumps(st.session_state.alerts_list, ensure_ascii=False, indent=2)
            st.download_button(
                "导出提醒配置",
                data=json_data,
                file_name="价格提醒配置.json",
                mime="application/json",
                use_container_width=True,
            )
        with batch_cols[3]:
            if st.button("清空全部", use_container_width=True):
                st.session_state.alerts_list = []
                st.rerun()

# ─── Tab 3: 触发历史 ────────────────────────────────────
with tab_history:
    history = st.session_state.get("alert_history", [])

    st.markdown("### 触发记录")

    if not history:
        st.info("暂无触发记录。")
    else:
        hdf = pd.DataFrame(
            [
                {
                    "触发时间": h.get("time", "--"),
                    "提醒名称": h.get("alert", "--"),
                    "代码": h.get("symbol", "--"),
                    "条件": CONDITION_CN.get(h.get("condition", ""), h.get("condition", "")),
                    "触发值": h.get("value_triggered", "--"),
                    "通知渠道": h.get("channel", "--"),
                    "已送达": "✅" if h.get("notified") else "❌",
                }
                for h in history
            ]
        )
        st.dataframe(hdf, use_container_width=True, hide_index=True)

        hcols = st.columns(3)
        with hcols[0]:
            st.metric("总触发次数", len(history))
        with hcols[1]:
            st.metric(
                "成功送达",
                sum(1 for h in history if h.get("notified")),
            )
        with hcols[2]:
            unique_alerts = len({h.get("alert", "") for h in history})
            st.metric("涉及提醒数", unique_alerts)

    st.markdown("---")
    st.caption(
        "提醒中心（本页）以演示 / 内存会话存储方式工作，数据随页面会话丢失。生产环境请对接数据库与实际通知渠道 API。"
    )

# ─── 页脚 ─────────────────────────────────────────────────
st.markdown("---")
st.caption("提示：提醒仅在用户会话有效期间生效，刷新或关闭页面会重置。")
