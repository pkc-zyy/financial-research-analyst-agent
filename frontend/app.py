"""
FinancialAI 智能研报平台 - AI 顾问首页
就股票、ETF、投资组合策略等问题与 AI 实时对话，基于实时行情数据给出建议。
"""

import streamlit as st
from components.header import render_header

from utils.data_service import (
    ask_advisor,
    get_stock_price,
    wiki_generate_chat_report,
    wiki_save_page,
)
from utils.formatters import format_currency, format_percent
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="FinancialAI 智能研报平台",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── 主题与状态 ───────────────────────────────────────────
inject_css()
init_session_state()

# ─── 顶部导航 ───────────────────────────────────────────────
render_header()

# ─── 分区标题渲染辅助函数 ───────────────────────────────────


def _section(title: str):
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1.25rem 0 1rem;">
            <div style="width: 3px; height: 20px; background: linear-gradient(180deg, #6366f1, #8b5cf6); border-radius: 2px;"></div>
            <h3 style="font-family: 'Inter', sans-serif; margin: 0; color: #fafafa; font-size: 0.9rem;
                        font-weight: 600; letter-spacing: -0.01em;">{title}</h3>
            <div style="flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,255,255,0.06), transparent);"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── 主视觉标题区 ─────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align: center; padding: 1.5rem 1rem 2.5rem; position: relative;">
        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    width: 400px; height: 400px; background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
                    pointer-events: none; z-index: 0;"></div>
        <h1 style="font-family: 'Inter', sans-serif; font-size: 2.25rem; font-weight: 800;
                   letter-spacing: -0.03em; margin-bottom: 0.5rem; position: relative; z-index: 1;">
            <span style="color: #fafafa;">AI 金融</span>
            <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                         -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                智能顾问
            </span>
        </h1>
        <p style="font-size: 0.9rem; color: #71717a; max-width: 520px; margin: 0 auto; line-height: 1.6; position: relative; z-index: 1;">
            随时提问关于股票、ETF、股息、投资组合策略或市场主题等问题，
            我将按需抓取实时数据，为您提供最相关的分析建议。
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── 大盘脉搏（精简版）──────────────────────────────────
indices = [
    ("SPY", "标普 500"),
    ("QQQ", "纳斯达克 100"),
    ("DIA", "道琼斯"),
    ("IWM", "罗素 2000"),
]

cols = st.columns(4)
for col, (ticker, label) in zip(cols, indices):
    with col:
        data = get_stock_price(ticker)
        if "error" not in data:
            price = data.get("current_price", 0)
            change = data.get("change_percent", 0)
            col.metric(
                label=label,
                value=format_currency(price),
                delta=format_percent(change),
            )
        else:
            col.metric(label=label, value="--", delta="暂无")

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

# ─── 初始化对话历史 ─────────────────────────────────
if "advisor_chat_history" not in st.session_state:
    st.session_state.advisor_chat_history = []

# ─── FAQ 快捷问题（对话为空时显示）────────────────
if not st.session_state.advisor_chat_history:
    _section("快捷提问")

    _faqs = [
        [
            "现在投资哪只 ETF 比较合适？",
            "新手最稳健的 3 只 ETF 是什么？",
            "我在 180 美元买入了 QQQM，该继续持有还是卖出？",
        ],
        [
            "对比 QQQ 和 VOO 哪个更适合长期投资？",
            "帮我构建一只 1 万美元的分散化 ETF 组合",
            "今年表现最好的行业板块有哪些？",
        ],
        [
            "被动收入首选的高股息 ETF 是什么？",
            "按当前价格，苹果 (AAPL) 值得买入吗？",
            "值得关注的 AI 头部股票是哪些？",
        ],
    ]

    for row in _faqs:
        cols = st.columns(3)
        for j, faq in enumerate(row):
            with cols[j]:
                if st.button(faq, key=f"adv_faq_{faq[:20]}", use_container_width=True):
                    st.session_state.advisor_faq_selected = faq
                    st.rerun()

else:
    # 有历史记录时显示文档生成与清空对话按钮
    col_report, col_clear, _ = st.columns([1.4, 1, 4])
    with col_report:
        generate_report = st.button("📄 一键生成分析文档", type="primary", use_container_width=True)
    with col_clear:
        if st.button("清空对话", use_container_width=True):
            st.session_state.advisor_chat_history = []
            st.session_state.pop("chat_report_draft", None)
            st.rerun()

# ─── 对话消息 ────────────────────────────────────────────
for msg in st.session_state.advisor_chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ─── 一键生成分析文档 ────────────────────────────────────
if not st.session_state.advisor_chat_history:
    st.session_state.pop("chat_report_draft", None)

if not st.session_state.advisor_chat_history:
    pass  # 无对话时不渲染文档区
elif generate_report:
    with st.spinner("🧠 LLM 正在根据对话内容撰写分析文档,约需 1 分钟……"):
        try:
            draft = wiki_generate_chat_report(
                st.session_state.advisor_chat_history,
                language="zh",
            )
            draft["saved_slug"] = None
            st.session_state.chat_report_draft = draft
        except Exception as e:
            st.session_state.pop("chat_report_draft", None)
            st.error(f"生成分析文档失败:{e}")

draft = st.session_state.get("chat_report_draft")
if draft and st.session_state.advisor_chat_history:
    turns_now = len(st.session_state.advisor_chat_history)
    stale = turns_now > draft.get("turns", 0)

    if draft.get("saved_slug"):
        st.success(
            f"✅ 文档已保存到 LLM Wiki(页面:{draft['saved_slug']})。可在左侧「LLM Wiki」页面查看。"
        )
    else:
        st.info(
            "分析文档已生成。可保存到 LLM Wiki 知识库,或下载为 Markdown 文件。"
            + (" ⚠️ 对话在此之后又有新消息,建议重新生成。" if stale else "")
        )

    with st.expander("📑 分析文档预览", expanded=not draft.get("saved_slug")):
        st.markdown(f"**{draft['title']}**")
        if draft.get("summary"):
            st.caption(draft["summary"])
        st.markdown(draft["content"])

    col_save, col_dl, _ = st.columns([1.4, 1.4, 4])
    with col_save:
        if st.button("💾 保存到 LLM Wiki", use_container_width=True):
            try:
                page = wiki_save_page(
                    title=draft["title"],
                    content=draft["content"],
                    category="analysis",
                    tags=draft.get("tags", []),
                    summary=draft.get("summary", ""),
                )
                draft["saved_slug"] = page["slug"]
                st.toast("文档已保存到知识库", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败:{e}")
    with col_dl:
        md_text = (
            f"# {draft['title']}\n\n"
            + (f"> {draft['summary']}\n\n" if draft.get("summary") else "")
            + draft["content"]
        )
        st.download_button(
            "⬇️ 下载 Markdown",
            data=md_text,
            file_name=f"{draft['title']}.md",
            mime="text/markdown",
            use_container_width=True,
        )

# ─── 对话输入框 ──────────────────────────────────────────
_faq_prompt = st.session_state.pop("advisor_faq_selected", None)
_typed_prompt = st.chat_input("提问任意股票、ETF、市场主题或投资策略相关问题……")
prompt = _faq_prompt or _typed_prompt

if prompt:
    st.session_state.advisor_chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 分步显示进度 + 图标
        status = st.status("正在分析您的问题……", expanded=True)

        _step_icons = {
            "profiling": "👤",
            "prefetch": "📡",
            "analyzing": "🧠",
            "lookup": "📊",
            "technical": "📈",
            "fundamentals": "📋",
            "dividends": "💰",
            "earnings": "📑",
            "sentiment": "📰",
            "peers": "🔄",
            "options": "⚡",
            "insider": "🔍",
            "synthesizing": "✨",
            "fallback": "🔁",
        }

        def _on_progress(key: str, label: str):
            icon = _step_icons.get(key, "⏳")
            status.update(label=f"{icon} {label}")
            status.write(f"{icon} {label}")

        response = ask_advisor(
            question=prompt,
            chat_history=st.session_state.advisor_chat_history[:-1],
            on_progress=_on_progress,
        )

        status.update(label="分析完成", state="complete", expanded=False)
        st.markdown(response)

    st.session_state.advisor_chat_history.append({"role": "assistant", "content": response})

# ─── 底部固定栏 ────────────────────────────────────────────
st.markdown(
    """
    <style>
        .fixed-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #09090b;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding: 0.75rem 1rem;
            text-align: center;
            z-index: 998;
        }
        .fixed-footer p {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            color: #52525b;
            margin: 0;
        }
        /* 为页面底部增加内边距，避免内容被底部栏遮挡 */
        [data-testid="stMainBlockContainer"] {
            padding-bottom: 3rem !important;
        }
    </style>
    <div class="fixed-footer">
        <p>Financial AI 智能金融平台 v1.0 — 仅供信息参考，不构成投资建议</p>
    </div>
    """,
    unsafe_allow_html=True,
)
