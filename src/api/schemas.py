from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class SourceModel(BaseModel):
    document_id: str
    chunk_id: str
    page_start: int
    page_end: int
    score: float


class ChatResponseModel(BaseModel):
    response: str
    sources: list[SourceModel]
    conversation_id: str


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[ConversationMessage]


class DocumentSummary(BaseModel):
    id: str
    title: str
    status: str
    pages: int | None = None
    chunks: int | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class DocumentContentResponse(BaseModel):
    id: str
    title: str
    content: str


class UploadResponse(BaseModel):
    document_id: str
    status: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class SearchResultModel(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    page_end: int
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultModel]


class HealthResponse(BaseModel):
    status: str
    ollama: str
    vector_db: str
    models_loaded: list[str]
    documents_indexed: int


class AdminAuthRequest(BaseModel):
    admin_password: str


class AdminAuthResponse(BaseModel):
    valid: bool
