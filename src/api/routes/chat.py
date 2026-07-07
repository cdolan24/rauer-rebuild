from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    ChatRequest,
    ChatResponseModel,
    ConversationHistoryResponse,
    ConversationMessage,
    SourceModel,
)
from src.rag.chat_engine import ChatResponse
from src.utils.ollama_client import OllamaError

router = APIRouter(tags=["chat"])


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/chat", response_model=ChatResponseModel)
def chat(payload: ChatRequest, request: Request) -> ChatResponseModel:
    chat_engine = request.app.state.chat_engine
    query_logger = request.app.state.query_logger

    start = time.monotonic()
    try:
        result = chat_engine.ask(payload.conversation_id, payload.message)
    except OllamaError as e:
        raise HTTPException(status_code=503, detail=f"Local LLM service unavailable: {e}") from e
    elapsed_ms = int((time.monotonic() - start) * 1000)

    query_logger.log(payload.conversation_id, payload.message, elapsed_ms)

    return ChatResponseModel(
        response=result.answer,
        sources=[
            SourceModel(
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                page_start=c.page_start,
                page_end=c.page_end,
                score=c.score,
            )
            for c in result.citations
        ],
        conversation_id=payload.conversation_id,
    )


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    chat_engine = request.app.state.chat_engine
    query_logger = request.app.state.query_logger

    def event_generator():
        start = time.monotonic()
        try:
            for item in chat_engine.ask_stream(payload.conversation_id, payload.message):
                if isinstance(item, ChatResponse):
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    query_logger.log(payload.conversation_id, payload.message, elapsed_ms)
                    yield _sse_event(
                        {
                            "type": "done",
                            "sources": [
                                {
                                    "document_id": c.document_id,
                                    "chunk_id": c.chunk_id,
                                    "page_start": c.page_start,
                                    "page_end": c.page_end,
                                    "score": c.score,
                                }
                                for c in item.citations
                            ],
                        }
                    )
                else:
                    yield _sse_event({"type": "token", "content": item})
        except OllamaError as e:
            yield _sse_event({"type": "error", "detail": f"Local LLM service unavailable: {e}"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation(conversation_id: str, request: Request) -> ConversationHistoryResponse:
    conversation_store = request.app.state.conversation_store
    history = conversation_store.get_history(conversation_id)

    messages: list[ConversationMessage] = []
    for turn in history:
        messages.append(ConversationMessage(role="user", content=turn.question))
        messages.append(ConversationMessage(role="assistant", content=turn.answer))

    return ConversationHistoryResponse(conversation_id=conversation_id, messages=messages)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request) -> dict[str, str]:
    conversation_store = request.app.state.conversation_store
    conversation_store.clear(conversation_id)
    return {"status": "cleared"}
