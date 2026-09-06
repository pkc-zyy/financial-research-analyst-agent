"""
LLM-powered wiki page generation.

Two generation modes:

- **Stock pages** — grounded in live data pulled from the existing tool layer
  (market data, financial statements, technical indicators, news) plus the RAG
  knowledge base when documents for the symbol have been ingested.
- **Concept pages** — explanatory entries for financial concepts (e.g. "Sharpe
  Ratio", "DCF Valuation") written by the LLM, cross-linked to related wiki
  pages when they exist.

Usage::

    from src.wiki.generator import WikiGenerator

    gen = WikiGenerator()
    draft = gen.generate_stock_page("AAPL")           # data-grounded research page
    draft = gen.generate_concept_page("Sharpe Ratio") # explainer page
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

LANGUAGES = {
    "zh": "Simplified Chinese (简体中文)",
    "en": "English",
}

STOCK_SECTIONS = [
    "公司概况",
    "业务与商业模式",
    "财务表现",
    "估值水平",
    "技术面信号",
    "近期市场动态",
    "风险因素",
    "投资要点总结",
]


def create_default_llm(temperature: float = 0.25):
    """Create a chat model instance from the configured provider (mirrors BaseAgent)."""
    from src.config import settings

    provider = settings.llm.provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm.model,
            temperature=temperature,
            api_key=settings.llm.openai_api_key,
            max_tokens=settings.llm.max_tokens,
            base_url=settings.llm.base_url or None,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm.model,
            api_key=settings.llm.anthropic_api_key,
            temperature=temperature,
            max_tokens=settings.llm.max_tokens,
        )
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.llm.groq_model,
            api_key=settings.llm.groq_api_key,
            temperature=temperature,
        )
    if provider == "lmstudio":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm.lmstudio_model,
            base_url=settings.llm.lmstudio_base_url,
            temperature=temperature,
            api_key="lm-studio",
        )
    if provider == "vllm":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm.vllm_model,
            base_url=settings.llm.vllm_base_url,
            temperature=temperature,
            api_key="vllm",
        )

    # ollama and unknown providers default to Ollama
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.llm.ollama_model,
        base_url=settings.llm.ollama_base_url,
        temperature=temperature,
    )


class WikiGenerator:
    """Generates wiki page drafts with the configured LLM."""

    def __init__(
        self,
        llm: Optional[Any] = None,
        temperature: float = 0.25,
        store: Optional[Any] = None,
    ) -> None:
        self.llm = llm or create_default_llm(temperature)
        # Optional WikiStore used for related-page cross-links. When omitted,
        # no cross-links are produced and the vector store is never touched
        # (loading it may pull embedding models from the network).
        self._store = store

    # ── Public API ───────────────────────────────────────────────

    def generate_stock_page(self, symbol: str, language: str = "zh") -> Dict[str, Any]:
        """Generate a data-grounded research wiki page for a stock ticker.

        Returns a dict ready for ``WikiStore.create_page`` (minus source).
        """
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol must not be empty")

        context, data_sources = self._gather_stock_context(symbol)
        lang = LANGUAGES.get(language, LANGUAGES["zh"])

        system_prompt = (
            "You are a senior equity research analyst maintaining an internal investment "
            "knowledge wiki. You write rigorous, neutral, well-structured wiki pages in "
            f"{lang}. Base every factual claim on the DATA block provided; when data is "
            "missing or marked unavailable, say so explicitly instead of inventing numbers. "
            "Never give personalized investment advice; end with a short disclaimer."
        )
        user_prompt = f"""Write a stock research wiki page about {symbol}.

Available data sources: {', '.join(data_sources) or 'none'}

=== DATA (collected live, may be partial) ===
{context}
=== END DATA ===

Requirements:
1. Output format — first line exactly: `SUMMARY: <one-sentence summary>`
2. Then a line with only `---`, then the page body in Markdown.
3. The body must use these top-level sections (as `## ` headings, translated into {lang}):
   {json.dumps(STOCK_SECTIONS, ensure_ascii=False)}
4. Quote concrete numbers from the data (price, market cap, P/E, RSI, MACD, margins...) with units.
5. In "风险因素" and "投资要点总结", stay balanced — no buy/sell pressure.
6. Add a final `> 免责声明` blockquote line noting this page is AI-generated from live data and is not investment advice.
7. Keep the whole page under ~1200 words."""

        content = self._invoke(system_prompt, user_prompt)
        summary, body = self._parse_response(content)

        return {
            "title": f"{symbol} 研究页面" if language == "zh" else f"{symbol} Research Page",
            "content": body,
            "category": "stock",
            "symbol": symbol,
            "tags": ["stock", symbol.lower(), "llm-generated"],
            "summary": summary,
            "model": self._model_name(),
            "meta": {"data_sources": data_sources, "mode": "stock"},
        }

    def generate_concept_page(
        self,
        topic: str,
        language: str = "zh",
        audience: str = "intermediate",
    ) -> Dict[str, Any]:
        """Generate an explanatory wiki page for a financial concept."""
        topic = (topic or "").strip()
        if not topic:
            raise ValueError("topic must not be empty")
        lang = LANGUAGES.get(language, LANGUAGES["zh"])
        related = self._related_pages(topic)

        system_prompt = (
            "You are a finance professor and CFA charterholder maintaining an internal "
            f"investment knowledge wiki. You write accurate, pedagogical wiki pages in {lang} "
            f"for a {audience}-level audience. Use precise definitions, show formulas, and "
            "always include a worked numeric example."
        )
        user_prompt = f"""Write a wiki page explaining the financial concept: "{topic}".

Output format:
1. First line exactly: `SUMMARY: <one-sentence definition>`
2. Then a line with only `---`, then the page body in Markdown.

The body must include these `## ` sections (translated into {lang}):
- 定义 (what it is, precise definition)
- 直觉理解 (intuition / why it matters)
- 计算方法 (formula(s) in LaTeX-style notation, each variable explained)
- 数值示例 (a small worked example with realistic numbers)
- 实务应用 (how practitioners use it, typical benchmarks/thresholds)
- 常见误区 (common pitfalls and misinterpretations)
- 相关概念 (related concepts, with brief links-in-words)

Keep it under ~900 words. Do not fabricate citations."""
        if related:
            user_prompt += (
                f"\n\nThese related wiki pages already exist (mention them in "
                f"相关概念 where genuinely relevant): {json.dumps(related, ensure_ascii=False)}"
            )

        content = self._invoke(system_prompt, user_prompt)
        summary, body = self._parse_response(content)

        return {
            "title": topic,
            "content": body,
            "category": "concept",
            "symbol": None,
            "tags": ["concept", "llm-generated"],
            "summary": summary,
            "model": self._model_name(),
            "meta": {"mode": "concept", "related_pages": related},
        }

    # ── Conversation report generation ───────────────────────────

    def generate_conversation_report(
        self,
        messages: List[Dict[str, str]],
        language: str = "zh",
    ) -> Dict[str, Any]:
        """Synthesize a completed advisory conversation into a standalone
        analysis document (Markdown), ready to save into the wiki.

        Args:
            messages: Chat history as [{"role": "user"|"assistant", "content": str}, ...].
            language: Output language key ("zh" or "en").

        Returns a dict ready for ``WikiStore.create_page`` (minus source).
        """
        conversation = _format_conversation(messages)
        if not conversation:
            raise ValueError("messages must contain at least one non-empty message")
        lang = LANGUAGES.get(language, LANGUAGES["zh"])

        system_prompt = (
            "You are a senior investment analyst writing formal analysis documents for an "
            f"internal knowledge base. You write in {lang}. You turn advisory conversations "
            "between a client and an AI financial advisor into rigorous, standalone analysis "
            "documents that a reader who never saw the conversation can understand. Base every "
            "claim strictly on what was established in the conversation; do not invent data. "
            "Keep the original disclaimer spirit: informational analysis, not personalized "
            "financial advice."
        )
        user_prompt = f"""Below is the transcript of a completed advisory conversation.

=== CONVERSATION ===
{conversation}
=== END CONVERSATION ===

Turn it into a formal analysis document.

Output format — first three lines exactly:
TITLE: <a specific, descriptive document title>
SUMMARY: <one-sentence executive summary>
TAGS: <3-5 comma-separated tags>
Then a line with only `---`, then the document body in Markdown.

The body must use these `## ` sections (translated into {lang}):
- 背景与客户关注点 (what the client asked about, their situation and goals)
- 关键数据与依据 (concrete numbers, tickers, metrics established in the conversation)
- 分析与解读 (the advisor's reasoning and interpretation)
- 结论与建议要点 (actionable takeaways as a concise list)
- 风险提示 (risks and caveats raised or implied)
- 免责声明 (final blockquote: AI-generated from an advisory conversation, informational only)

Do not mention the conversation transcript mechanics ("the user said..."); rewrite as a
document. Keep it under ~1200 words."""

        content = self._invoke(system_prompt, user_prompt)
        title, summary, tags, body = self._parse_report_response(content, language)

        return {
            "title": title,
            "content": body,
            "category": "analysis",
            "symbol": None,
            "tags": tags,
            "summary": summary,
            "model": self._model_name(),
            "meta": {"mode": "conversation", "turns": len(messages)},
        }

    @staticmethod
    def _parse_report_response(text: str, language: str = "zh") -> Tuple[str, str, List[str], str]:
        """Split `TITLE:/SUMMARY:/TAGS:/---/<body>` into its parts."""
        default_title = "对话分析报告" if language == "zh" else "Conversation Analysis Report"

        def _header(pattern: str) -> Optional[str]:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            return match.group(1).strip().strip("*").strip() if match else None

        title = _header(r"^\s*\**TITLE:?\**\s*(.+)$") or default_title
        summary = _header(r"^\s*\**SUMMARY:?\**\s*(.+)$") or ""
        tags_line = _header(r"^\s*\**TAGS:?\**\s*(.+)$") or ""
        tags = [t.strip().strip("#") for t in tags_line.split(",") if t.strip()]
        tags = tags or ["analysis", "llm-generated"]

        # Body starts after the separator line that follows the header block
        summary_match = re.search(r"^\s*\**SUMMARY", text, flags=re.IGNORECASE | re.MULTILINE)
        search_start = summary_match.start() if summary_match else 0
        separator = re.search(r"^\s*[-*_]{3,}\s*$", text[search_start:], flags=re.MULTILINE)
        body = text[search_start + separator.end() :].strip() if separator else text.strip()

        return title, summary, tags, body or text.strip()

    # ── Data gathering for stock pages ───────────────────────────

    def _gather_stock_context(self, symbol: str) -> Tuple[str, List[str]]:
        """Collect live data for a symbol into a compact text block."""
        sections: List[str] = []
        sources: List[str] = []

        price = self._try(f"quote({symbol})", lambda: _fmt_json(_market_price(symbol)))
        if price:
            sections.append(f"### Quote\n{price}")
            sources.append("Yahoo Finance quote")

        info = self._try(f"company_info({symbol})", lambda: _fmt_json(_company_info(symbol)))
        if info:
            sections.append(f"### Company Profile\n{info}")
            sources.append("company profile")

        fundamentals = self._try(
            f"financial_statements({symbol})", lambda: _fmt_json(_financials(symbol))
        )
        if fundamentals:
            sections.append(f"### Financial Statements (most recent)\n{fundamentals}")
            sources.append("financial statements")

        technicals = self._try(f"technicals({symbol})", lambda: _fmt_json(_technicals(symbol)))
        if technicals:
            sections.append(f"### Technical Indicators\n{technicals}")
            sources.append("technical indicators")

        news = self._try(f"news({symbol})", lambda: _fmt_json(_news(symbol)))
        if news:
            sections.append(f"### Recent News Headlines\n{news}")
            sources.append("news headlines")

        rag = self._try(
            f"rag_context({symbol})",
            lambda: _rag_context(symbol),
        )
        if rag:
            sections.append(f"### Knowledge Base Excerpts (SEC filings / transcripts)\n{rag}")
            sources.append("RAG knowledge base")

        if not sections:
            sections.append(
                "(No live data could be collected. Write the page using only clearly "
                "labeled general knowledge, and note that live data was unavailable.)"
            )

        return "\n\n".join(sections), sources

    def _try(self, label: str, fn) -> Optional[str]:
        try:
            result = fn()
            return result or None
        except Exception as e:
            logger.warning(f"Wiki data source '{label}' unavailable: {e}")
            return None

    def _related_pages(self, topic: str, top_k: int = 5) -> List[Dict[str, str]]:
        if self._store is None:
            return []
        try:
            hits = self._store.semantic_search(topic, top_k=top_k)
            return [{"slug": h["slug"], "title": h["title"]} for h in hits if h["slug"]]
        except Exception as e:
            logger.debug(f"Related wiki page lookup skipped: {e}")
            return []

    # ── LLM invocation & parsing ─────────────────────────────────

    def _invoke(self, system_prompt: str, user_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = self.llm.invoke(messages)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        text = (content or "").strip()
        if not text:
            raise RuntimeError("LLM returned an empty wiki page")
        return text

    @staticmethod
    def _parse_response(text: str) -> Tuple[str, str]:
        """Split `SUMMARY: ...\\n---\\n<body>` into (summary, body)."""
        match = re.search(r"^\s*\**SUMMARY:?\**\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        summary = ""
        body = text
        if match:
            summary = match.group(1).strip().strip("*").strip()
            remainder_start = match.end()
            body_after = text[remainder_start:]
            # Drop a leading separator line (--- or ***)
            body_after = re.sub(r"^\s*[-*_]{3,}\s*", "", body_after, count=1)
            body = body_after.strip() or text.strip()
        else:
            summary = text.strip().split("\n")[0][:200]
        return summary, body

    def _model_name(self) -> str:
        for attr in ("model_name", "model"):
            value = getattr(self.llm, attr, None)
            if isinstance(value, str) and value:
                return value
        return ""


# ── Data source helpers (imported lazily so failures stay local) ─────

CONVERSATION_BUDGET_CHARS = 12000


def _format_conversation(messages: List[Dict[str, str]], budget: int = CONVERSATION_BUDGET_CHARS) -> str:
    """Format chat history into a transcript, keeping it inside the prompt budget.

    Oversized transcripts keep the first user message (the original question)
    plus the most recent tail, eliding the middle.
    """
    lines: List[str] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content", "") or "").strip()
        if not content:
            continue
        role = "Client" if msg.get("role") == "user" else "AI Advisor"
        lines.append(f"{role}: {content}")
    if not lines:
        return ""

    text = "\n\n".join(lines)
    if len(text) <= budget:
        return text

    elided = "\n\n[... middle of the conversation elided ...]\n\n"
    first = lines[0]
    tail_budget = max(budget - len(first) - len(elided), 1000)
    return first + elided + text[-tail_budget:]


def _fmt_json(data: Any, max_chars: int = 3000) -> Optional[str]:
    if not data:
        return None
    if isinstance(data, dict) and data.get("error"):
        return None
    text = json.dumps(data, default=str, ensure_ascii=False)
    return text[:max_chars]


def _market_price(symbol: str) -> Dict[str, Any]:
    from src.tools.market_data import get_stock_price

    return get_stock_price(symbol)


def _company_info(symbol: str) -> Dict[str, Any]:
    from src.tools.market_data import get_company_info

    return get_company_info(symbol)


def _financials(symbol: str) -> Dict[str, Any]:
    from src.tools.market_data import get_financial_statements

    statements = get_financial_statements(symbol)
    # Keep only the most recent column of each statement to bound prompt size
    if isinstance(statements, dict):
        trimmed: Dict[str, Any] = {}
        for key, value in statements.items():
            if isinstance(value, dict):
                trimmed[key] = {k: v for k, v in list(value.items())[:8]}
            else:
                trimmed[key] = value
        return trimmed
    return statements


def _technicals(symbol: str) -> Dict[str, Any]:
    from src.tools.market_data import get_historical_data
    from src.tools.technical_indicators import (
        calculate_macd,
        calculate_moving_averages,
        calculate_rsi,
    )

    hist = get_historical_data(symbol, period="6mo")
    if isinstance(hist, dict) and hist.get("error"):
        return hist
    closes = hist.get("closes") or []
    if not closes:
        return {"error": "no price history"}
    result = {
        "period": hist.get("period", "6mo"),
        "last_close": closes[-1] if closes else None,
        "rsi_14": calculate_rsi(closes),
        "macd": calculate_macd(closes),
        "moving_averages": calculate_moving_averages(closes),
    }
    # Drop raw series arrays to keep the prompt compact
    for block in ("rsi_14", "macd", "moving_averages"):
        if isinstance(result.get(block), dict):
            result[block] = {
                k: v for k, v in result[block].items() if not isinstance(v, (list, tuple))
            }
    return result


def _news(symbol: str, max_items: int = 6) -> List[Dict[str, Any]]:
    from src.tools.news_fetcher import fetch_company_news

    articles = fetch_company_news(symbol) or []
    return [
        {
            "title": a.get("title", ""),
            "source": a.get("source", ""),
            "published": a.get("published_at", "") or a.get("published", ""),
            "summary": (a.get("description") or a.get("summary") or "")[:200],
        }
        for a in articles[:max_items]
    ]


def _rag_context(symbol: str) -> Optional[str]:
    from src.rag.retriever import RAGRetriever

    retriever = RAGRetriever()
    if not retriever.has_documents(symbol):
        return None
    return retriever.get_context_for_llm(
        f"{symbol} business model, competitive position, and risk factors",
        symbol=symbol,
        top_k=4,
        max_context_chars=4000,
    )
