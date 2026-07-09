from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import admin, auth, chat, documents, health, search
from src.wiki.routes import router as wiki_router
from src.database.document_registry import DocumentRegistry
from src.database.entity_store import EntityStore
from src.database.query_logger import QueryLogger
from src.database.vector_store import VectorStore
from src.rag.chat_engine import ChatEngine
from src.rag.conversation_store import ConversationStore
from src.rag.retriever import Retriever
from src.utils.config import get_config_path, load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config(get_config_path())
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    vector_store = VectorStore(config.vector_db.path, config.vector_db.collection_name)
    registry = DocumentRegistry(config.data_storage_path)
    entity_store = EntityStore(config.data_storage_path)
    query_logger = QueryLogger(config.data_storage_path)
    conversation_store = ConversationStore()
    retriever = Retriever(
        vector_store, ollama_client, config.ollama.embedding_model, entity_store=entity_store
    )
    chat_engine = ChatEngine(
        retriever,
        ollama_client,
        conversation_store,
        chat_model=config.ollama.chat_model,
        min_score=config.rag_min_score,
        num_predict=config.ollama.num_predict,
        keep_alive=config.ollama.keep_alive,
        max_history_turns=config.rag_max_history_turns,
    )

    app.state.config = config
    app.state.ollama_client = ollama_client
    app.state.vector_store = vector_store
    app.state.registry = registry
    app.state.entity_store = entity_store
    app.state.query_logger = query_logger
    app.state.conversation_store = conversation_store
    app.state.retriever = retriever
    app.state.chat_engine = chat_engine

    logger.info("Buddharauer API started.")
    yield
    logger.info("Buddharauer API shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(title="Buddharauer API", lifespan=lifespan)

    config = load_config(get_config_path())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(chat.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(wiki_router)

    return app


app = create_app()
