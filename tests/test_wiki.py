"""
Tests for the LLM Wiki module (store, generator, API endpoints).
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import persistence as persistence_module
from src.wiki.generator import WikiGenerator
from src.wiki.store import WIKI_CATEGORIES, WikiStore, chunk_text, slugify


# ── Fakes ────────────────────────────────────────────────────


class FakeEmbedder:
    """In-memory stand-in for the ChromaDB Embedder (keyword overlap scoring)."""

    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}

    def add_documents(self, texts, metadatas=None, ids=None) -> None:
        for i, text in enumerate(texts):
            doc_id = ids[i] if ids else f"doc-{len(self.docs)}-{i}"
            self.docs[doc_id] = {
                "text": text,
                "metadata": (metadatas[i] if metadatas else {}) or {},
            }

    def query(self, query_text: str, n_results: int = 5, where: Optional[Dict] = None, **_):
        candidates = [
            (doc_id, doc)
            for doc_id, doc in self.docs.items()
            if not where or all(doc["metadata"].get(k) == v for k, v in where.items())
        ]
        q_tokens = set(query_text.lower().split())

        def score(doc):
            tokens = set(doc["text"].lower().split())
            overlap = len(q_tokens & tokens)
            return overlap / (len(q_tokens) or 1)

        ranked = sorted(candidates, key=lambda pair: -score(pair[1]))[:n_results]
        return {
            "documents": [doc["text"] for _, doc in ranked],
            "metadatas": [doc["metadata"] for _, doc in ranked],
            "distances": [max(0.0, 2.0 * (1.0 - score(doc))) for _, doc in ranked],
            "ids": [doc_id for doc_id, _ in ranked],
        }

    def delete_where(self, where: Dict[str, Any]) -> int:
        matched = [
            doc_id
            for doc_id, doc in self.docs.items()
            if all(doc["metadata"].get(k) == v for k, v in where.items())
        ]
        for doc_id in matched:
            self.docs.pop(doc_id, None)
        return len(matched)

    def count(self) -> int:
        return len(self.docs)

    def reset(self) -> None:
        self.docs.clear()


class FakeLLM:
    """Minimal chat model returning a canned SUMMARY-formatted response."""

    def __init__(self, content: str, model_name: str = "fake-model"):
        self.content = content
        self.model_name = model_name
        self.calls: List[List[Any]] = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self.content)


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def wiki_env(tmp_path, monkeypatch):
    """Isolated wiki environment: temp SQLite DB + FakeEmbedder-backed store."""
    engine = create_engine(f"sqlite:///{tmp_path / 'wiki_test.db'}")
    TestSessionFactory = sessionmaker(bind=engine)
    persistence_module.Base.metadata.create_all(engine)
    monkeypatch.setattr(persistence_module, "_engine", engine)
    monkeypatch.setattr(persistence_module, "_SessionFactory", TestSessionFactory)

    monkeypatch.setattr(WikiStore, "_tables_ready", True, raising=False)
    monkeypatch.setattr("src.wiki.store._wiki_store", None)

    store = WikiStore(embedder=FakeEmbedder())
    yield store
    monkeypatch.setattr("src.wiki.store._wiki_store", None)


@pytest.fixture
def api_client(wiki_env, monkeypatch):
    """TestClient for a standalone app carrying only the wiki router."""
    from src.api import wiki_routes

    monkeypatch.setattr(wiki_routes, "get_wiki_store", lambda: wiki_env)

    test_app = FastAPI()
    test_app.include_router(wiki_routes.router)
    return TestClient(test_app)


# ── Store unit tests ─────────────────────────────────────────


class TestSlugify:
    def test_ascii_title(self):
        assert slugify("Sharpe Ratio!") == "sharpe-ratio"

    def test_cjk_title_preserved(self):
        assert "夏普比率" in slugify("夏普比率 说明")

    def test_empty_fallback(self):
        assert slugify("!!!") == "page"


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "A short page."
        assert chunk_text(text) == [text]

    def test_empty_text(self):
        assert chunk_text("") == []

    def test_long_text_splits_with_overlap(self):
        text = "\n\n".join(f"paragraph {i} " + "word " * 100 for i in range(10))
        chunks = chunk_text(text)
        assert len(chunks) > 1
        assert all(c.strip() for c in chunks)


class TestWikiStoreCRUD:
    def test_create_and_get(self, wiki_env):
        page = wiki_env.create_page(
            title="Sharpe Ratio",
            content="# Sharpe Ratio\nRisk-adjusted return.",
            category="concept",
            tags=["risk", "metrics"],
            summary="A ratio.",
        )
        assert page["slug"] == "sharpe-ratio"
        assert page["source"] == "manual"

        fetched = wiki_env.get_page("sharpe-ratio")
        assert fetched is not None
        assert fetched["title"] == "Sharpe Ratio"
        assert fetched["tags"] == ["risk", "metrics"]
        assert "Risk-adjusted" in fetched["content"]

    def test_duplicate_title_gets_unique_slug(self, wiki_env):
        first = wiki_env.create_page(title="Beta", content="b1")
        second = wiki_env.create_page(title="Beta", content="b2")
        assert first["slug"] != second["slug"]
        assert second["slug"].startswith("beta-")

    def test_invalid_category_normalized(self, wiki_env):
        page = wiki_env.create_page(title="Odd", content="x", category="not-a-category")
        assert page["category"] == "other"

    def test_update_fields_and_symbol_normalization(self, wiki_env):
        wiki_env.create_page(title="Alpha", content="old", symbol="aapl")
        updated = wiki_env.update_page("alpha", content="new", symbol="msft", tags=["t1"])
        assert updated["content"] == "new"
        assert updated["symbol"] == "MSFT"
        assert updated["tags"] == ["t1"]

    def test_update_missing_page_returns_none(self, wiki_env):
        assert wiki_env.update_page("nope", content="x") is None

    def test_delete(self, wiki_env):
        wiki_env.create_page(title="Gamma", content="g")
        assert wiki_env.delete_page("gamma") is True
        assert wiki_env.get_page("gamma") is None
        assert wiki_env.delete_page("gamma") is False

    def test_empty_title_rejected(self, wiki_env):
        with pytest.raises(ValueError):
            wiki_env.create_page(title="  ", content="x")


class TestWikiStoreListing:
    @pytest.fixture(autouse=True)
    def seed(self, wiki_env):
        wiki_env.create_page(
            title="AAPL Research", content="apple phone", category="stock", symbol="AAPL", tags=["tech"]
        )
        wiki_env.create_page(title="DCF 估值", content="discounted cash flow", category="concept")
        wiki_env.create_page(title="Momentum 策略", content="buy winners", category="strategy", tags=["momentum"])

    def test_list_total_and_order(self, wiki_env):
        result = wiki_env.list_pages()
        assert result["total"] == 3
        titles = [p["title"] for p in result["pages"]]
        assert "AAPL Research" in titles

    def test_filter_category(self, wiki_env):
        result = wiki_env.list_pages(category="concept")
        assert result["total"] == 1
        assert result["pages"][0]["title"] == "DCF 估值"

    def test_filter_symbol(self, wiki_env):
        result = wiki_env.list_pages(symbol="aapl")
        assert result["total"] == 1
        assert result["pages"][0]["slug"] == "aapl-research"

    def test_filter_tag_case_insensitive(self, wiki_env):
        result = wiki_env.list_pages(tag="MOMENTUM")
        assert result["total"] == 1

    def test_keyword_search(self, wiki_env):
        result = wiki_env.list_pages(q="cash flow")
        assert result["total"] == 1
        assert result["pages"][0]["title"] == "DCF 估值"

    def test_pagination(self, wiki_env):
        result = wiki_env.list_pages(limit=2, offset=0)
        assert len(result["pages"]) == 2
        result = wiki_env.list_pages(limit=2, offset=2)
        assert len(result["pages"]) == 1


class TestWikiSemanticSearch:
    def test_search_finds_indexed_chunks(self, wiki_env):
        wiki_env.create_page(
            title="Sharpe Ratio",
            content="Sharpe ratio measures risk adjusted return per unit of volatility.",
            category="concept",
        )
        hits = wiki_env.semantic_search("risk adjusted return metric", top_k=3)
        assert hits, "expected at least one semantic hit"
        assert hits[0]["slug"] == "sharpe-ratio"
        assert 0.0 <= hits[0]["score"] <= 1.0

    def test_search_after_delete(self, wiki_env):
        wiki_env.create_page(title="Temp", content="unique zebra content")
        assert wiki_env.delete_page("temp")
        assert wiki_env.semantic_search("zebra") == []

    def test_reindex_all(self, wiki_env):
        wiki_env.create_page(title="P1", content="one two three", indexed=False)
        wiki_env.create_page(title="P2", content="four five six", indexed=False)
        wiki_env.embedder.reset()
        chunks = wiki_env.reindex_all()
        assert chunks >= 2
        assert wiki_env.stats()["indexed_chunks"] == chunks

    def test_stats_counts(self, wiki_env):
        wiki_env.create_page(title="S1", content="a", category="stock", source="llm")
        stats = wiki_env.stats()
        assert stats["total"] == 1
        assert stats["by_category"] == {"stock": 1}
        assert stats["by_source"] == {"llm": 1}


# ── Generator tests ──────────────────────────────────────────


SUMMARY_RESPONSE = """SUMMARY: 夏普比率是衡量风险调整后收益的指标。
---
## 定义

夏普比率 = (Rp - Rf) / σp

## 计算方法

公式如上,σp 为组合收益波动率。"""


class TestWikiGenerator:
    def test_concept_page_parses_summary_and_body(self):
        llm = FakeLLM(SUMMARY_RESPONSE)
        gen = WikiGenerator(llm=llm)
        draft = gen.generate_concept_page("夏普比率", language="zh")

        assert draft["category"] == "concept"
        assert draft["title"] == "夏普比率"
        assert draft["summary"] == "夏普比率是衡量风险调整后收益的指标。"
        assert draft["content"].startswith("## 定义")
        assert draft["model"] == "fake-model"
        assert len(llm.calls) == 1
        # System + user message layout
        assert len(llm.calls[0]) == 2

    def test_parse_response_without_summary_marker(self):
        summary, body = WikiGenerator._parse_response("Just some text\nline two")
        assert summary == "Just some text"
        assert "line two" in body

    def test_concept_page_cross_links_related_pages(self, wiki_env):
        wiki_env.create_page(
            title="Sharpe Ratio",
            content="sharpe ratio risk adjusted return volatility benchmark",
            category="concept",
        )
        llm = FakeLLM(SUMMARY_RESPONSE)
        gen = WikiGenerator(llm=llm, store=wiki_env)
        draft = gen.generate_concept_page("Sharpe Ratio", language="zh")

        related = draft["meta"]["related_pages"]
        assert any(r["slug"] == "sharpe-ratio" for r in related)
        # Cross-links must be mentioned in the prompt sent to the LLM
        assert "sharpe-ratio" in llm.calls[0][1].content

    def test_stock_page_uses_gathered_data(self, monkeypatch):
        monkeypatch.setattr(
            "src.wiki.generator._market_price", lambda s: {"symbol": s, "current_price": 180.5}
        )
        monkeypatch.setattr(
            "src.wiki.generator._company_info", lambda s: {"name": "Apple Inc.", "sector": "Technology"}
        )
        monkeypatch.setattr(
            "src.wiki.generator._financials",
            lambda s: {"income_statement": {"total_revenue": 400_000_000_000}},
        )
        monkeypatch.setattr(
            "src.wiki.generator._technicals",
            lambda s: {"rsi_14": {"rsi": 55.2}, "last_close": 180.5},
        )
        monkeypatch.setattr(
            "src.wiki.generator._news",
            lambda s, max_items=6: [{"title": "Apple announces new product", "source": "Reuters"}],
        )
        monkeypatch.setattr("src.wiki.generator._rag_context", lambda s: None)

        llm = FakeLLM("SUMMARY: Apple research page.\n---\n## 公司概况\nApple makes iPhones.")
        gen = WikiGenerator(llm=llm)
        draft = gen.generate_stock_page("aapl", language="zh")

        assert draft["symbol"] == "AAPL"
        assert draft["category"] == "stock"
        assert "AAPL" in draft["title"]
        assert draft["summary"] == "Apple research page."
        # Live data must be part of the prompt sent to the LLM
        prompt_text = llm.calls[0][1].content
        assert "180.5" in prompt_text
        assert "Apple announces new product" in prompt_text
        assert draft["meta"]["data_sources"], "data sources should be listed"

    def test_stock_page_requires_symbol(self):
        gen = WikiGenerator(llm=FakeLLM("x"))
        with pytest.raises(ValueError):
            gen.generate_stock_page("  ")


# ── API endpoint tests ───────────────────────────────────────


class TestWikiAPI:
    def test_create_get_update_delete_cycle(self, api_client):
        r = api_client.post(
            "/api/v1/wiki",
            json={"title": "Momentum", "content": "Buy winners.", "category": "strategy"},
        )
        assert r.status_code == 201
        slug = r.json()["slug"]
        assert slug == "momentum"

        r = api_client.get("/api/v1/wiki/momentum")
        assert r.status_code == 200
        assert r.json()["content"] == "Buy winners."

        r = api_client.put("/api/v1/wiki/momentum", json={"summary": "Trend following"})
        assert r.status_code == 200
        assert r.json()["summary"] == "Trend following"

        r = api_client.delete("/api/v1/wiki/momentum")
        assert r.status_code == 200
        assert api_client.get("/api/v1/wiki/momentum").status_code == 404

    def test_list_with_filters(self, api_client):
        api_client.post("/api/v1/wiki", json={"title": "Stock Page", "category": "stock", "symbol": "TSLA"})
        api_client.post("/api/v1/wiki", json={"title": "Concept Page", "category": "concept"})

        r = api_client.get("/api/v1/wiki", params={"category": "stock"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["pages"][0]["symbol"] == "TSLA"
        assert "content" not in data["pages"][0], "listings must not include full content"

    def test_search_endpoint(self, api_client):
        api_client.post(
            "/api/v1/wiki",
            json={"title": "Value Investing", "content": "buy undervalued stocks margin of safety"},
        )
        r = api_client.post("/api/v1/wiki/search", json={"query": "margin of safety", "top_k": 2})
        assert r.status_code == 200
        results = r.json()["results"]
        assert results and results[0]["slug"] == "value-investing"

    def test_generate_requires_symbol_for_stock_mode(self, api_client):
        r = api_client.post("/api/v1/wiki/generate", json={"mode": "stock"})
        assert r.status_code == 422

    def test_generate_concept_page_saved(self, api_client, monkeypatch):
        from src.api import wiki_routes

        class FakeGen:
            def generate_concept_page(self, topic, language="zh"):
                return {
                    "title": topic,
                    "content": f"## {topic}",
                    "category": "concept",
                    "symbol": None,
                    "tags": ["concept", "llm-generated"],
                    "summary": f"About {topic}",
                    "model": "fake-model",
                    "meta": {"mode": "concept", "related_pages": []},
                }

        monkeypatch.setattr(wiki_routes, "get_generator", lambda: FakeGen())

        r = api_client.post(
            "/api/v1/wiki/generate", json={"mode": "concept", "topic": "久期", "save": True}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["saved"] is True
        assert data["page"]["slug"]
        assert data["page"]["source"] == "llm"

        # Page persisted
        slug = data["page"]["slug"]
        assert api_client.get(f"/api/v1/wiki/{slug}").status_code == 200

    def test_stats_endpoint(self, api_client):
        api_client.post("/api/v1/wiki", json={"title": "Solo", "category": "macro"})
        r = api_client.get("/api/v1/wiki/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["by_category"] == {"macro": 1}

    def test_unknown_page_404(self, api_client):
        assert api_client.get("/api/v1/wiki/does-not-exist").status_code == 404


def test_categories_registry():
    assert set(WIKI_CATEGORIES) == {
        "stock",
        "concept",
        "strategy",
        "sector",
        "macro",
        "analysis",
        "other",
    }


# ── Conversation report generation ───────────────────────────

REPORT_RESPONSE = """TITLE: QQQM 持仓决策分析
SUMMARY: 综合估值与动量信号后建议继续持有并设置止损位。
TAGS: QQQM, 持有, ETF, 止损
---
## 背景与客户关注点

客户在 180 美元买入 QQQM,关注是否继续持有。

## 结论与建议要点

- 继续持有
- 设置 165 美元止损"""


class TestConversationReport:
    def _messages(self):
        return [
            {"role": "user", "content": "我在 180 美元买入了 QQQM，该继续持有还是卖出？"},
            {"role": "assistant", "content": "当前 QQQM 动量良好,估值中性,建议继续持有并设置止损。"},
        ]

    def test_parses_headers_and_body(self):
        llm = FakeLLM(REPORT_RESPONSE)
        gen = WikiGenerator(llm=llm)
        draft = gen.generate_conversation_report(self._messages(), language="zh")

        assert draft["title"] == "QQQM 持仓决策分析"
        assert draft["summary"].startswith("综合估值")
        assert draft["tags"] == ["QQQM", "持有", "ETF", "止损"]
        assert draft["category"] == "analysis"
        assert draft["content"].startswith("## 背景与客户关注点")
        assert draft["meta"]["turns"] == 2
        # The transcript must be part of the prompt
        assert "180" in llm.calls[0][1].content

    def test_fallbacks_when_headers_missing(self):
        llm = FakeLLM("## 背景与客户关注点\n\n没有头部行的一段正文。")
        gen = WikiGenerator(llm=llm)
        draft = gen.generate_conversation_report(self._messages())

        assert draft["title"] == "对话分析报告"
        assert draft["tags"] == ["analysis", "llm-generated"]
        assert "正文" in draft["content"]

    def test_empty_messages_rejected(self):
        gen = WikiGenerator(llm=FakeLLM("x"))
        with pytest.raises(ValueError):
            gen.generate_conversation_report([{"role": "user", "content": "   "}])

    def test_long_conversation_truncated_with_budget(self):
        from src.wiki.generator import CONVERSATION_BUDGET_CHARS, _format_conversation

        big = [{"role": "user", "content": "第一问：起点"}]
        big += [
            {"role": "assistant", "content": f"回复 {i} " + "x" * 500}
            for i in range(60)
        ]
        text = _format_conversation(big)
        assert len(text) <= CONVERSATION_BUDGET_CHARS + 100
        assert "起点" in text, "original question must be preserved"
        assert "elided" in text

    def test_whitespace_only_filtered(self):
        from src.wiki.generator import _format_conversation

        assert _format_conversation([{"role": "user", "content": "  "}, {}, None]) == ""


class TestChatReportAPI:
    def test_generate_report_endpoint(self, api_client, monkeypatch):
        from src.api import wiki_routes

        class FakeGen:
            def generate_conversation_report(self, messages, language="zh"):
                assert messages[0]["role"] == "user"
                return {
                    "title": "对话分析报告",
                    "content": "## 结论",
                    "category": "analysis",
                    "symbol": None,
                    "tags": ["analysis"],
                    "summary": "摘要",
                    "model": "fake-model",
                    "meta": {"mode": "conversation", "turns": len(messages)},
                }

        monkeypatch.setattr(wiki_routes, "get_generator", lambda: FakeGen())

        r = api_client.post(
            "/api/v1/wiki/generate-report",
            json={
                "messages": [
                    {"role": "user", "content": "该买入 AAPL 吗?"},
                    {"role": "assistant", "content": "综合来看……"},
                ],
                "save": True,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["saved"] is True
        assert data["turns"] == 2
        assert data["page"]["category"] == "analysis"
        assert data["page"]["source"] == "llm"

        slug = data["page"]["slug"]
        assert api_client.get(f"/api/v1/wiki/{slug}").status_code == 200
        api_client.delete(f"/api/v1/wiki/{slug}")

    def test_generate_report_requires_messages(self, api_client):
        r = api_client.post("/api/v1/wiki/generate-report", json={"messages": []})
        assert r.status_code == 422

    def test_analysis_category_accepted_in_create(self, api_client):
        r = api_client.post(
            "/api/v1/wiki",
            json={"title": "Report Page", "category": "analysis", "content": "x"},
        )
        assert r.status_code == 201
        assert r.json()["category"] == "analysis"
        api_client.delete("/api/v1/wiki/report-page")
