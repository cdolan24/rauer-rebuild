from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.schemas import SearchRequest, SearchResponse, SearchResultModel

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, request: Request) -> SearchResponse:
    retriever = request.app.state.retriever
    results = retriever.retrieve(payload.query, top_k=payload.limit)

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
