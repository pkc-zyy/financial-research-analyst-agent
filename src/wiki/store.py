"""
Wiki page store — CRUD over the ``wiki_pages`` table plus semantic index sync.

Every page is chunked and upserted into a dedicated ChromaDB collection
(``wiki_pages``) so wiki content is retrievable via semantic search and can
later serve as extra context for agents and reports.

Usage::

    from src.wiki.store import WikiStore

    store = WikiStore()
    page = store.create_page(
        title="Sharpe Ratio",
        content="# Sharpe Ratio\\n...",
        category="concept",
        tags=["risk", "metrics"],
    )
    results = store.semantic_search("risk adjusted return")
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.models.persistence import WikiPage, get_session, init_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

WIKI_CATEGORIES = ["stock", "concept", "strategy", "sector", "macro", "analysis", "other"]

VECTOR_COLLECTION = "wiki_pages"

# Rough chunk sizing, aligned with the RAG ingester (chars ≈ tokens * 4)
CHUNK_CHARS = 2048
CHUNK_OVERLAP = 256


def slugify(title: str) -> str:
    """Turn a page title into a URL-safe slug (CJK preserved)."""
    text = unicodedata.normalize("NFKC", title).strip().lower()
    # Keep latin letters, digits, whitespace, hyphens and CJK
    text = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:80] or "page"


def chunk_text(text: str) -> List[str]:
    """Split wiki content into overlapping chunks on paragraph boundaries."""
    if len(text) <= CHUNK_CHARS:
        return [text] if text.strip() else []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            # Prefer breaking on a paragraph/heading boundary within the overlap zone
            zone = text[max(start, end - CHUNK_OVERLAP) : end]
            for sep in ["\n\n", "\n"]:
                pos = zone.rfind(sep)
                if pos != -1:
                    end = end - CHUNK_OVERLAP + pos + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)

    return chunks


class WikiStore:
    """CRUD + vector index management for LLM Wiki pages."""

    _tables_ready = False

    def __init__(self, embedder: Optional[Any] = None) -> None:
        self._ensure_tables()
        self._embedder = embedder
        self._embedder_ready = embedder is not None

    @classmethod
    def _ensure_tables(cls) -> None:
        """Create persistence tables once (idempotent)."""
        if not cls._tables_ready:
            init_db()
            cls._tables_ready = True

    # ── Vector index (lazy — sentence-transformers load is expensive) ──

    @property
    def embedder(self) -> Any:
        if not self._embedder_ready:
            from src.rag.embedder import Embedder

            self._embedder = Embedder(collection_name=VECTOR_COLLECTION)
            self._embedder_ready = True
        return self._embedder

    def _index_page(self, page: WikiPage) -> int:
        """Chunk a page and upsert it into the vector collection."""
        chunks = chunk_text(page.content or "")
        if not chunks:
            return 0
        metadatas = [
            {
                "slug": page.slug,
                "title": page.title,
                "category": page.category or "other",
                "symbol": (page.symbol or "").upper(),
                "source": page.source or "manual",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]
        ids = [f"wiki:{page.slug}:{i}" for i in range(len(chunks))]
        self.embedder.add_documents(chunks, metadatas, ids)
        return len(chunks)

    def _deindex_page(self, slug: str) -> None:
        """Remove a page's chunks from the vector collection."""
        try:
            deleted = self.embedder.delete_where({"slug": slug})
            if deleted:
                logger.debug(f"Removed {deleted} indexed chunks for wiki page '{slug}'")
        except Exception as e:
            logger.warning(f"Vector de-index failed for '{slug}': {e}")

    # ── CRUD ─────────────────────────────────────────────────────

    def create_page(
        self,
        title: str,
        content: str,
        category: str = "other",
        tags: Optional[List[str]] = None,
        symbol: Optional[str] = None,
        summary: str = "",
        source: str = "manual",
        model: str = "",
        slug: Optional[str] = None,
        indexed: bool = True,
    ) -> Dict[str, Any]:
        """Create a wiki page and index it. Returns the page as a dict."""
        if not title or not title.strip():
            raise ValueError("Wiki page title must not be empty")
        if category not in WIKI_CATEGORIES:
            category = "other"

        session = get_session()
        base = slugify(slug or title)
        candidate, suffix = base, 2
        while session.query(WikiPage).filter_by(slug=candidate).first() is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1

        page = WikiPage(
            slug=candidate,
            title=title.strip(),
            category=category,
            symbol=(symbol or "").upper() or None,
            tags=[t.strip() for t in (tags or []) if t and t.strip()],
            summary=(summary or "").strip(),
            content=content or "",
            source=source if source in ("manual", "llm") else "manual",
            model=model or "",
        )
        session.add(page)
        session.commit()

        if indexed:
            try:
                self._index_page(page)
            except Exception as e:
                logger.warning(f"Vector indexing failed for new page '{page.slug}': {e}")

        result = self._to_dict(page)
        logger.info(f"Created wiki page '{page.slug}' (category={page.category})")
        return result

    def get_page(self, slug: str) -> Optional[Dict[str, Any]]:
        """Fetch a single page by slug."""
        session = get_session()
        page = session.query(WikiPage).filter_by(slug=slug).first()
        return self._to_dict(page) if page else None

    def update_page(self, slug: str, **fields: Any) -> Optional[Dict[str, Any]]:
        """Update an existing page. Allowed fields: title, content, category,
        tags, symbol, summary, model. Re-indexes the vector store."""
        allowed = {"title", "content", "category", "tags", "symbol", "summary", "model"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_page(slug)

        if "category" in updates and updates["category"] not in WIKI_CATEGORIES:
            updates["category"] = "other"
        if "symbol" in updates:
            updates["symbol"] = (updates["symbol"] or "").upper() or None
        if "tags" in updates:
            updates["tags"] = [t.strip() for t in (updates["tags"] or []) if t and t.strip()]

        session = get_session()
        page = session.query(WikiPage).filter_by(slug=slug).first()
        if page is None:
            return None

        for key, value in updates.items():
            setattr(page, key, value)
        page.updated_at = datetime.now(timezone.utc)
        session.commit()

        try:
            self._deindex_page(slug)
            self._index_page(page)
        except Exception as e:
            logger.warning(f"Vector re-index failed for '{slug}': {e}")

        logger.info(f"Updated wiki page '{slug}'")
        return self._to_dict(page)

    def delete_page(self, slug: str) -> bool:
        """Delete a page and remove it from the vector index."""
        session = get_session()
        page = session.query(WikiPage).filter_by(slug=slug).first()
        if page is None:
            return False
        session.delete(page)
        session.commit()
        self._deindex_page(slug)
        logger.info(f"Deleted wiki page '{slug}'")
        return True

    # ── Listing & search ─────────────────────────────────────────

    def list_pages(
        self,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
        tag: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List pages with optional filters. Returns {pages, total}."""
        session = get_session()
        query = session.query(WikiPage)

        if category:
            query = query.filter(WikiPage.category == category)
        if symbol:
            query = query.filter(WikiPage.symbol == symbol.upper())
        if q:
            pattern = f"%{q}%"
            query = query.filter(
                WikiPage.title.ilike(pattern)
                | WikiPage.summary.ilike(pattern)
                | WikiPage.content.ilike(pattern)
            )

        pages = query.order_by(WikiPage.updated_at.desc()).all()

        if tag:
            pages = [p for p in pages if tag.lower() in [t.lower() for t in (p.tags or [])]]

        total = len(pages)
        window = pages[offset : offset + limit]
        return {"total": total, "pages": [self._to_dict(p, include_content=False) for p in window]}

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search over indexed wiki chunks."""
        if not query or not query.strip():
            return []

        where: Dict[str, Any] = {}
        if category:
            where["category"] = category
        if symbol:
            where["symbol"] = symbol.upper()

        try:
            raw = self.embedder.query(
                query_text=query,
                n_results=top_k,
                where=where or None,
            )
        except Exception as e:
            logger.error(f"Wiki semantic search failed: {e}")
            return []

        results = []
        for text, meta, dist, _id in zip(
            raw["documents"], raw["metadatas"], raw["distances"], raw["ids"]
        ):
            results.append(
                {
                    "slug": meta.get("slug", ""),
                    "title": meta.get("title", ""),
                    "category": meta.get("category", "other"),
                    "symbol": meta.get("symbol", "") or None,
                    "chunk_index": meta.get("chunk_index", 0),
                    "snippet": text[:300],
                    "score": round(max(0.0, 1.0 - (dist / 2.0)), 3),
                }
            )
        return results

    def reindex_all(self) -> int:
        """Rebuild the vector index from scratch. Returns indexed chunk count."""
        try:
            self.embedder.reset()
        except Exception as e:
            logger.warning(f"Vector reset failed during reindex: {e}")

        session = get_session()
        pages = session.query(WikiPage).all()
        total_chunks = 0
        for page in pages:
            try:
                total_chunks += self._index_page(page)
            except Exception as e:
                logger.warning(f"Reindex failed for '{page.slug}': {e}")
        logger.info(f"Wiki reindex complete: {len(pages)} pages, {total_chunks} chunks")
        return total_chunks

    def stats(self) -> Dict[str, Any]:
        """Aggregate stats: totals by category/source and index size."""
        session = get_session()
        pages = session.query(WikiPage).all()
        by_category: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        for p in pages:
            by_category[p.category or "other"] = by_category.get(p.category or "other", 0) + 1
            by_source[p.source or "manual"] = by_source.get(p.source or "manual", 0) + 1
        try:
            indexed = self.embedder.count()
        except Exception:
            indexed = 0
        return {"total": len(pages), "by_category": by_category, "by_source": by_source, "indexed_chunks": indexed}

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _to_dict(page: WikiPage, include_content: bool = True) -> Dict[str, Any]:
        data = {
            "id": page.id,
            "slug": page.slug,
            "title": page.title,
            "category": page.category or "other",
            "symbol": page.symbol,
            "tags": page.tags or [],
            "summary": page.summary or "",
            "source": page.source or "manual",
            "model": page.model or "",
            "created_at": page.created_at.isoformat() if page.created_at else None,
            "updated_at": page.updated_at.isoformat() if page.updated_at else None,
        }
        if include_content:
            data["content"] = page.content or ""
        return data


# Module-level singleton for API/frontend usage
_wiki_store: Optional[WikiStore] = None


def get_wiki_store() -> WikiStore:
    """Get or create the shared WikiStore instance."""
    global _wiki_store
    if _wiki_store is None:
        _wiki_store = WikiStore()
    return _wiki_store
