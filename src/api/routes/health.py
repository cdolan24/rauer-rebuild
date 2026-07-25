from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    ollama_client = request.app.state.ollama_client
    chat_backend = request.app.state.chat_backend
    registry = request.app.state.registry

    # Embeddings always depend on Ollama, regardless of the configured chat
    # backend - checked unconditionally. Chat backend is checked separately
    # since it may not be Ollama (see src/utils/chat_backend.py).
    ollama_healthy, models = ollama_client.is_healthy()
    chat_backend_healthy, chat_backend_label = chat_backend.is_healthy()
    documents_indexed = sum(1 for r in registry.list_all() if r.status == "processed")

    return HealthResponse(
        status="healthy" if (ollama_healthy and chat_backend_healthy) else "degraded",
        ollama="connected" if ollama_healthy else "unreachable",
        vector_db="healthy",
        models_loaded=models,
        documents_indexed=documents_indexed,
        chat_backend=chat_backend_label,
        chat_backend_status="connected" if chat_backend_healthy else "unreachable",
    )
