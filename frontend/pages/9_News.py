"""
新闻中心 - 浏览多只股票的最新财经新闻。
"""

import streamlit as st
from components.header import render_header
from components.metrics_cards import render_news_card

from utils.data_service import get_company_news
from utils.formatters import format_date
from utils.session import init_session_state
from utils.theme import inject_css

# ─── 页面配置 ─────────────────────────────────────────────
st.set_page_config(
    page_title="财经新闻 | 智能金融 AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
init_session_state()
render_header()

st.markdown("## 财经新闻")
st.caption("来自 Yahoo Finance 的最新要闻速递")

# ─── 来源选择 ────────────────────────────────────────────
watchlist = st.session_state.get("watchlist", ["AAPL", "MSFT", "GOOGL"])
default_sym = st.session_state.get("selected_symbol", "") or ""

c1, c2 = st.columns([2, 1])
with c1:
    custom = st.text_input(
        "搜索股票新闻",
        value=default_sym,
        placeholder="例如 AAPL、NVDA",
        key="news_symbol_input",
    )
with c2:
    st.markdown("<br>", unsafe_allow_html=True)
    use_watchlist = st.checkbox("包含自选股", value=True, key="news_watchlist_toggle")

# 构建待获取的股票列表
symbols = []
if custom:
    symbols.extend([s.strip().upper() for s in custom.split(",") if s.strip()])
if use_watchlist:
    for s in watchlist:
        if s not in symbols:
            symbols.append(s)

if not symbols:
    st.info("请输入股票代码或勾选『包含自选股』以查看新闻。")
    st.stop()

# ─── 获取并合并新闻 ─────────────────────────────────────
all_articles = []
for sym in symbols:
    news = get_company_news(sym)
    for article in news:
        article["_symbol"] = sym
        all_articles.append(article)


# 按日期排序（最新在前）
def _sort_key(article):
    d = article.get("published_at", "")
    return d if d else "0"


all_articles.sort(key=_sort_key, reverse=True)

# 按标题去重
seen_titles = set()
unique_articles = []
for a in all_articles:
    title = a.get("title", "")
    if title and title not in seen_titles:
        seen_titles.add(title)
        unique_articles.append(a)

st.markdown(
    f"**共 {len(unique_articles)} 篇文章** 来自 {len(symbols)} 个来源：{', '.join(symbols)}"
)
st.markdown("---")

if not unique_articles:
    st.info("未找到所选股票的相关新闻。")
    st.stop()

# ─── 头条新闻 ───────────────────────────────────────
featured = unique_articles[0]
st.markdown(
    f"""
    <div class="news-card" style="padding: 0; overflow: hidden;">
        {"<img src='" + featured.get('thumbnail', '') + "' style='width: 100%; height: 200px; object-fit: cover;' onerror=\"this.style.display='none'\" />" if featured.get('thumbnail') else ""}
        <div style="padding: 1.25rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <span style="font-size: 0.65rem; padding: 0.15rem 0.5rem; border-radius: 999px;
                             background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.25);
                             font-weight: 600;">{featured.get('_symbol', '')}</span>
                <span style="font-size: 0.65rem; color: #6b7280;">
                    {featured.get('source', '')} &middot; {format_date(featured.get('published_at', ''))}
                </span>
            </div>
            <a href="{featured.get('url', '#')}" target="_blank"
               style="color: #f9fafb; text-decoration: none; font-weight: 700; font-size: 1.25rem; line-height: 1.3;">
                {featured.get('title', '无标题')}
            </a>
            <p style="color: #9ca3af; font-size: 0.875rem; margin-top: 0.5rem; line-height: 1.5;">
                {featured.get('description', '')[:300]}
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

# ─── 新闻网格 ───────────────────────────────────────
# 过滤器控件
filter_col1, filter_col2 = st.columns([1, 3])
with filter_col1:
    type_filter = st.selectbox(
        "类型",
        ["全部", "文章", "视频"],
        key="news_type_filter",
        label_visibility="collapsed",
    )
with filter_col2:
    symbol_filter = st.multiselect(
        "按股票过滤",
        symbols,
        default=symbols,
        key="news_symbol_filter",
        label_visibility="collapsed",
    )

# 应用过滤
filtered = unique_articles[1:]  # 跳过头条
if type_filter == "文章":
    filtered = [a for a in filtered if a.get("type", "").upper() != "VIDEO"]
elif type_filter == "视频":
    filtered = [a for a in filtered if a.get("type", "").upper() == "VIDEO"]

if symbol_filter:
    filtered = [a for a in filtered if a.get("_symbol") in symbol_filter]

# 渲染网格
cols = st.columns(2)
for i, article in enumerate(filtered[:20]):
    with cols[i % 2]:
        sym_badge = (
            f'<span style="display: inline-block; font-size: 0.6rem; padding: 0.1rem 0.4rem; '
            f"border-radius: 999px; background: rgba(59, 130, 246, 0.1); color: #3b82f6; "
            f"border: 1px solid rgba(59, 130, 246, 0.2); font-weight: 600; "
            f'margin-right: 0.25rem;">{article.get("_symbol", "")}</span>'
        )

        render_news_card(
            title=article.get("title", "无标题"),
            source=f'{sym_badge} {article.get("source", "")}',
            date=format_date(article.get("published_at", "")),
            description=article.get("description", ""),
            url=article.get("url", ""),
            thumbnail=article.get("thumbnail", ""),
            content_type=article.get("type", ""),
        )

if not filtered:
    st.caption("当前筛选条件下没有匹配的文章。")
