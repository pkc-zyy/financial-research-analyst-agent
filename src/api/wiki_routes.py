"""
LLM Wiki API endpoints.

Mounted under ``/api/v1/wiki`` and included by ``src.api.routes``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import (
    WikiChatReportRequest,
    WikiChatReportResponse,
    WikiGenerateRequest,
    WikiGenerateResponse,
    WikiListResponse,
    WikiPageCreate,
    WikiPageResponse,
    WikiPageSummary,
    WikiPageUpdate,
    WikiSearchRequest,
    WikiSearchResponse,
    WikiSearchResult,
    WikiStatsResponse,
)
from src.utils.logger import get_logger
from src.wiki.generator import WikiGenerator
from src.wiki.store import WikiStore, get_wiki_store

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])

_generator = None


def get_generator() -> WikiGenerator:
    """Get or create the shared WikiGenerator (LLM-backed)."""
    global _generator
    if _generator is None:
        _generator = WikiGenerator(store=get_wiki_store())
    return _generator


def _to_page_response(page: dict) -> WikiPageResponse:
    return WikiPageResponse(**page)


def _to_page_summary(page: dict) -> WikiPageSummary:
    data = {k: v for k, v in page.items() if k != "content"}
    return WikiPageSummary(**data)


@router.get("", response_model=WikiListResponse)
async def list_wiki_pages(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    symbol: Optional[str] = Query(default=None, description="Filter by ticker"),
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
    q: Optional[str] = Query(default=None, description="Keyword search in title/summary/content"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List wiki pages with optional filters."""
    try:
        result = get_wiki_store().list_pages(
            category=category, symbol=symbol, tag=tag, q=q, limit=limit, offset=offset
        )
        return WikiListResponse(
            total=result["total"], pages=[_to_page_summary(p) for p in result["pages"]]
        )
    except Exception as e:
        logger.error(f"Wiki list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=WikiStatsResponse)
async def wiki_stats():
    """Aggregate wiki statistics."""
    try:
        return WikiStatsResponse(**get_wiki_store().stats())
    except Exception as e:
        logger.error(f"Wiki stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=WikiSearchResponse)
async def search_wiki(request: WikiSearchRequest):
    """Semantic search over wiki content (vector index)."""
    try:
        hits = get_wiki_store().semantic_search(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            symbol=request.symbol,
        )
        return WikiSearchResponse(
            query=request.query, results=[WikiSearchResult(**h) for h in hits]
        )
    except Exception as e:
        logger.error(f"Wiki search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=WikiGenerateResponse)
async def generate_wiki_page(request: WikiGenerateRequest):
    """Generate a wiki page with the LLM (stock research page or concept explainer)."""
    start = time.time()
    if request.mode == "stock" and not request.symbol:
        raise HTTPException(status_code=422, detail="mode=stock requires 'symbol'")
    if request.mode == "concept" and not request.topic:
        raise HTTPException(status_code=422, detail="mode=concept requires 'topic'")

    try:
        generator = get_generator()
        # LLM + data gathering are blocking — run them off the event loop
        if request.mode == "stock":
            draft = await asyncio.to_thread(
                generator.generate_stock_page, request.symbol.strip().upper(), request.language
            )
        else:
            draft = await asyncio.to_thread(
                generator.generate_concept_page, request.topic.strip(), request.language
            )

        page = draft
        saved = False
        if request.save:
            store: WikiStore = get_wiki_store()
            page = store.create_page(
                title=draft["title"],
                content=draft["content"],
                category=draft["category"],
                tags=draft["tags"],
                symbol=draft.get("symbol"),
                summary=draft["summary"],
                source="llm",
                model=draft["model"],
            )
            saved = True

        return WikiGenerateResponse(
            page=_to_page_response(page),
            saved=saved,
            data_sources=draft.get("meta", {}).get("data_sources", []),
            generation_time_seconds=round(time.time() - start, 2),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Wiki generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Wiki generation failed: {e}")


@router.post("/generate-report", response_model=WikiChatReportResponse)
async def generate_chat_report(request: WikiChatReportRequest):
    """Synthesize a completed advisory conversation into a standalone
    analysis document (optionally saved to the wiki as category=analysis)."""
    start = time.time()
    try:
        generator = get_generator()
        draft = await asyncio.to_thread(
            generator.generate_conversation_report,
            [m.model_dump() for m in request.messages],
            request.language,
        )

        page = draft
        saved = False
        if request.save:
            page = get_wiki_store().create_page(
                title=draft["title"],
                content=draft["content"],
                category=draft["category"],
                tags=draft["tags"],
                symbol=draft.get("symbol"),
                summary=draft["summary"],
                source="llm",
                model=draft["model"],
            )
            saved = True

        return WikiChatReportResponse(
            page=_to_page_response(page),
            saved=saved,
            turns=len(request.messages),
            generation_time_seconds=round(time.time() - start, 2),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Chat report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat report generation failed: {e}")


@router.post("", response_model=WikiPageResponse, status_code=201)
async def create_wiki_page(request: WikiPageCreate):
    """Create a wiki page manually."""
    try:
        page = get_wiki_store().create_page(
            title=request.title,
            content=request.content,
            category=request.category,
            tags=request.tags,
            symbol=request.symbol,
            summary=request.summary,
            source="manual",
        )
        return _to_page_response(page)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Wiki create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}", response_model=WikiPageResponse)
async def get_wiki_page(slug: str):
    """Fetch a single wiki page by slug."""
    page = get_wiki_store().get_page(slug)
    if page is None:
        raise HTTPException(status_code=404, detail=f"Wiki page '{slug}' not found")
    return _to_page_response(page)


@router.put("/{slug}", response_model=WikiPageResponse)
async def update_wiki_page(slug: str, request: WikiPageUpdate):
    """Update a wiki page (partial update)."""
    page = get_wiki_store().update_page(slug, **request.model_dump(exclude_none=True))
    if page is None:
        raise HTTPException(status_code=404, detail=f"Wiki page '{slug}' not found")
    return _to_page_response(page)


@router.delete("/{slug}")
async def delete_wiki_page(slug: str):
    """Delete a wiki page."""
    deleted = get_wiki_store().delete_page(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Wiki page '{slug}' not found")
    return {"status": "deleted", "slug": slug}


@router.post("/reindex")
async def reindex_wiki():
    """Rebuild the wiki vector index from all stored pages."""
    try:
        chunks = await asyncio.to_thread(get_wiki_store().reindex_all)
        return {"status": "ok", "indexed_chunks": chunks}
    except Exception as e:
        logger.error(f"Wiki reindex failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
