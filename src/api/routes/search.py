from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import SearchRequest, SearchResponse, SearchResultModel
from src.utils.ollama_client import OllamaError

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, request: Request) -> SearchResponse:
    retriever = request.app.state.retriever
    try:
        results = retriever.retrieve(payload.query, top_k=payload.limit)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=f"Local LLM service unavailable: {e}") from e

    return SearchResponse(
        results=[
            SearchResultModel(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                text=r.text,
                page_start=r.page_start,
                page_end=r.page_end,
                score=r.score,
            )
            for r in results
        ]
    )
