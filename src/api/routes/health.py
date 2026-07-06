from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    ollama_client = request.app.state.ollama_client
    registry = request.app.state.registry

    ollama_healthy, models = ollama_client.is_healthy()
    documents_indexed = sum(1 for r in registry.list_all() if r.status == "processed")

    return HealthResponse(
        status="healthy" if ollama_healthy else "degraded",
        ollama="connected" if ollama_healthy else "unreachable",
        vector_db="healthy",
        models_loaded=models,
        documents_indexed=documents_indexed,
    )
