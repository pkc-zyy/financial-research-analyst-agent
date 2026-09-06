"""
LLM Wiki —— AI 生成与维护的投资研究知识库。

- 浏览:按分类/关键词浏览 Wiki 页面,支持在线编辑与删除
- 语义搜索:基于向量的全文语义检索
- LLM 生成:股票研究页(结合实时行情/财报/新闻数据)与金融概念解释页
- 新建页面:手动撰写 Markdown 知识页
"""

import streamlit as st
from components.header import render_header

from utils.data_service import (
    wiki_delete_page,
    wiki_generate_page,
    wiki_get_page,
    wiki_list_pages,
    wiki_save_page,
    wiki_semantic_search,
    wiki_stats,
    wiki_update_page,
)
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="LLM Wiki | 智能金融 AI",
    page_icon=":books:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

CATEGORY_LABELS = {
    "stock": "📈 股票研究",
    "concept": "💡 概念解释",
    "strategy": "🎯 策略方法",
    "sector": "🏭 行业板块",
    "macro": "🌍 宏观经济",
    "analysis": "🧾 对话分析",
    "other": "📄 其他",
}
LABEL_TO_CATEGORY = {v: k for k, v in CATEGORY_LABELS.items()}

st.markdown("## LLM Wiki 知识库")
st.caption("由 LLM 生成与维护的投资研究知识库 —— 支持语义搜索,内容可编辑、可扩充")


def _badge(text: str, color: str = "#3b82f6") -> str:
    return (
        f'<span style="display:inline-block;font-size:0.62rem;padding:0.12rem 0.5rem;'
        f"border-radius:999px;background:{color}22;color:{color};"
        f'border:1px solid {color}44;font-weight:600;margin-right:0.3rem;">{text}</span>'
    )


def _parse_tags(raw: str) -> list:
    return [t.strip() for t in raw.split(",") if t.strip()]


def _render_page_detail(page: dict):
    """渲染单页详情:元信息 + Markdown 正文 + 编辑/删除。"""
    cat = CATEGORY_LABELS.get(page.get("category", "other"), "📄 其他")
    badges = _badge(cat)
    if page.get("symbol"):
        badges += _badge(page["symbol"], "#10b981")
    for tag in page.get("tags", [])[:6]:
        badges += _badge(f"#{tag}", "#6b7280")
    st.markdown(badges, unsafe_allow_html=True)

    source = "LLM 生成" if page.get("source") == "llm" else "手动创建"
    meta_bits = [f"来源:{source}"]
    if page.get("model"):
        meta_bits.append(f"模型:{page['model']}")
    if page.get("updated_at"):
        meta_bits.append(f"更新:{page['updated_at'][:16].replace('T', ' ')}")
    st.caption(" · ".join(meta_bits))

    if page.get("summary"):
        st.info(page["summary"])

    st.markdown(page.get("content", ""))

    col1, col2, _ = st.columns([1, 1, 6])
    slug = page["slug"]

    with col1:
        if st.button("✏️ 编辑此页", key=f"wiki_edit_{slug}"):
            st.session_state["wiki_editing"] = slug
            st.rerun()
    with col2:
        with st.popover("🗑️ 删除", use_container_width=True):
            st.warning(f"确定删除「{page['title']}」?此操作不可恢复。")
            if st.button("确认删除", key=f"wiki_del_{slug}", type="primary"):
                wiki_delete_page(slug)
                st.session_state.pop("wiki_selected_slug", None)
                st.session_state.pop("wiki_editing", None)
                st.toast("页面已删除", icon="🗑️")
                st.rerun()

    # ── 编辑表单 ──
    if st.session_state.get("wiki_editing") == slug:
        st.markdown("#### 编辑页面")
        with st.form(f"wiki_edit_form_{slug}"):
            title = st.text_input("标题", value=page["title"])
            cat_col, sym_col = st.columns(2)
            with cat_col:
                category = st.selectbox(
                    "分类",
                    list(CATEGORY_LABELS.values()),
                    index=list(CATEGORY_LABELS.keys()).index(page.get("category", "other")),
                )
            with sym_col:
                symbol = st.text_input("关联股票(可选)", value=page.get("symbol") or "")
            summary = st.text_input("一句话摘要", value=page.get("summary", ""))
            content = st.text_area("正文(Markdown)", value=page.get("content", ""), height=420)
            if st.form_submit_button("💾 保存修改", type="primary"):
                try:
                    wiki_update_page(
                        slug,
                        title=title,
                        category=LABEL_TO_CATEGORY[category],
                        symbol=symbol or None,
                        summary=summary,
                        content=content,
                    )
                    st.session_state.pop("wiki_editing", None)
                    st.toast("修改已保存", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败:{e}")


# ─── 统计概览 ─────────────────────────────────────────────
try:
    stats = wiki_stats()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 页面总数", stats.get("total", 0))
    m2.metric("🤖 LLM 生成", stats.get("by_source", {}).get("llm", 0))
    m3.metric("✍️ 手动创建", stats.get("by_source", {}).get("manual", 0))
    m4.metric("🧠 已索引片段", stats.get("indexed_chunks", 0))
except Exception as e:
    st.error(f"知识库初始化失败:{e}")
    st.stop()

# ─── 当前选中页详情(置于 Tabs 之上,浏览/搜索跳转共用) ──
selected_slug = st.session_state.get("wiki_selected_slug")
if selected_slug:
    selected_page = wiki_get_page(selected_slug)
    if selected_page:
        if st.button("← 返回列表"):
            st.session_state.pop("wiki_selected_slug", None)
            st.session_state.pop("wiki_editing", None)
            st.rerun()
        st.markdown("---")
        _render_page_detail(selected_page)
        st.markdown("---")
    else:
        st.warning("页面不存在,可能已被删除。")
        st.session_state.pop("wiki_selected_slug", None)

tab_browse, tab_search, tab_generate, tab_new = st.tabs(
    ["📖 浏览", "🔍 语义搜索", "✨ LLM 生成", "✏️ 新建页面"]
)

# ─── Tab 1:浏览 ───────────────────────────────────────────
with tab_browse:
    f1, f2 = st.columns([1, 2])
    with f1:
        cat_pick = st.selectbox("分类", ["全部"] + list(CATEGORY_LABELS.values()), key="wiki_cat")
    with f2:
        kw = st.text_input("关键词(标题/摘要/正文)", key="wiki_kw", placeholder="例如:夏普、AAPL")

    category = None if cat_pick == "全部" else LABEL_TO_CATEGORY[cat_pick]
    try:
        pages = wiki_list_pages(category=category, q=kw or None)
    except Exception as e:
        st.error(f"读取页面列表失败:{e}")
        pages = []

    if not selected_slug:
        if not pages:
            st.info("暂无页面。切换到「✨ LLM 生成」或「✏️ 新建页面」开始构建你的知识库。")
        else:
            st.markdown(f"**共 {len(pages)} 个页面**")
            for p in pages:
                cat = CATEGORY_LABELS.get(p.get("category", "other"), "📄 其他")
                sym = f" · {p['symbol']}" if p.get("symbol") else ""
                src_icon = "🤖" if p.get("source") == "llm" else "✍️"
                if st.button(
                    f"{src_icon} {p['title']}", key=f"wiki_open_{p['slug']}", use_container_width=True
                ):
                    st.session_state["wiki_selected_slug"] = p["slug"]
                    st.rerun()
                st.caption(f"{cat}{sym} · {p.get('summary', '')[:80]}")
    else:
        st.caption("当前正在查看一个页面,详情见上方;点击「← 返回列表」可继续浏览。")

# ─── Tab 2:语义搜索 ───────────────────────────────────────
with tab_search:
    q = st.text_input(
        "语义搜索(自然语言)",
        key="wiki_search_q",
        placeholder="例如:衡量风险调整后收益的指标 / AAPL 的主要风险",
    )
    if st.button("🔍 搜索", type="primary") and q:
        with st.spinner("正在检索知识库……"):
            try:
                results = wiki_semantic_search(q, top_k=8)
            except Exception as e:
                st.error(f"搜索失败:{e}")
                results = []
        if not results:
            st.info("没有匹配的内容。若刚创建页面,请确认向量索引可用(需要安装 sentence-transformers)。")
        for r in results:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{r['title']}**")
                    st.caption(f"相关度 {r['score']:.0%} · {CATEGORY_LABELS.get(r['category'], '📄 其他')}")
                    st.markdown(f"> {r['snippet'][:200]}…")
                with c2:
                    if st.button("查看全文", key=f"wiki_goto_{r['slug']}_{r['chunk_index']}"):
                        st.session_state["wiki_selected_slug"] = r["slug"]
                        st.rerun()

# ─── Tab 3:LLM 生成 ───────────────────────────────────────
with tab_generate:
    mode_label = st.radio(
        "生成模式",
        ["📈 股票研究页(结合实时数据)", "💡 概念解释页"],
        key="wiki_gen_mode",
        horizontal=True,
    )
    mode = "stock" if mode_label.startswith("📈") else "concept"

    if mode == "stock":
        g1, g2 = st.columns([1, 2])
        with g1:
            symbol = st.text_input("股票代码", value=st.session_state.get("selected_symbol", "") or "AAPL", key="wiki_gen_symbol").strip().upper()
        with g2:
            language = st.selectbox("输出语言", ["中文", "English"], key="wiki_gen_lang")
        st.caption("将自动拉取行情、公司资料、财务报表、技术指标与近期新闻作为写作素材,生成后可编辑。")
    else:
        g1, g2 = st.columns([2, 1])
        with g1:
            topic = st.text_input("概念主题", key="wiki_gen_topic", placeholder="例如:夏普比率、DCF 估值、久期")
        with g2:
            language = st.selectbox("输出语言", ["中文", "English"], key="wiki_gen_lang_c")

    if st.button("✨ 生成页面", type="primary", key="wiki_gen_btn"):
        lang = "zh" if language == "中文" else "en"
        try:
            with st.spinner("🤖 LLM 正在撰写页面(含数据采集),约需 1-2 分钟……"):
                if mode == "stock":
                    draft = wiki_generate_page("stock", symbol=symbol, language=lang)
                else:
                    draft = wiki_generate_page("concept", topic=topic, language=lang)
            st.session_state["wiki_draft"] = draft
        except Exception as e:
            st.session_state.pop("wiki_draft", None)
            st.error(f"生成失败:{e}")

    draft = st.session_state.get("wiki_draft")
    if draft:
        st.success(
            f"生成完成 —— 模型:{draft.get('model', '?')}"
            + (
                f" · 数据来源:{', '.join(draft['meta'].get('data_sources', []))}"
                if draft.get("meta", {}).get("data_sources")
                else ""
            )
        )
        st.markdown("#### 预览")
        st.markdown(draft["content"])
        if st.button("💾 保存到知识库", type="primary"):
            try:
                page = wiki_save_page(
                    title=draft["title"],
                    content=draft["content"],
                    category=draft["category"],
                    tags=draft["tags"],
                    symbol=draft.get("symbol"),
                    summary=draft["summary"],
                )
                st.session_state.pop("wiki_draft", None)
                st.session_state["wiki_selected_slug"] = page["slug"]
                st.toast(f"已保存:{page['title']}", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"保存失败:{e}")

# ─── Tab 4:新建页面 ───────────────────────────────────────
with tab_new:
    with st.form("wiki_new_form"):
        title = st.text_input("标题", key="wiki_new_title", placeholder="例如:我的核心卫星策略")
        n1, n2 = st.columns(2)
        with n1:
            category = st.selectbox("分类", list(CATEGORY_LABELS.values()), key="wiki_new_cat")
        with n2:
            symbol = st.text_input("关联股票(可选)", key="wiki_new_symbol")
        tags = st.text_input("标签(逗号分隔)", key="wiki_new_tags", placeholder="value, momentum")
        summary = st.text_input("一句话摘要", key="wiki_new_summary")
        content = st.text_area(
            "正文(Markdown)",
            key="wiki_new_content",
            height=420,
            placeholder="# 标题\n\n支持标准 Markdown 语法……",
        )
        if st.form_submit_button("💾 创建页面", type="primary"):
            if not title.strip():
                st.error("标题不能为空")
            else:
                try:
                    page = wiki_save_page(
                        title=title,
                        content=content,
                        category=LABEL_TO_CATEGORY[category],
                        tags=_parse_tags(tags),
                        symbol=symbol or None,
                        summary=summary,
                    )
                    st.session_state["wiki_selected_slug"] = page["slug"]
                    st.toast(f"已创建:{page['title']}", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败:{e}")
