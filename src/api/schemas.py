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
    source_type: str = "text"


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
    source_type: str = "text"


class SearchResponse(BaseModel):
    results: list[SearchResultModel]


class HealthResponse(BaseModel):
    status: str
    ollama: str
    vector_db: str
    models_loaded: list[str]
    documents_indexed: int
    # The configured chat-generation backend ("ollama" or "hosted_api") and
    # its own reachability - separate from `ollama` above, which reports the
    # embeddings dependency that's always active regardless of chat backend.
    chat_backend: str
    chat_backend_status: str


class AdminAuthRequest(BaseModel):
    admin_password: str


class AdminAuthResponse(BaseModel):
    valid: bool


class AdminQueryRequest(BaseModel):
    admin_password: str
    sql: str


class AdminQueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    rows_affected: int | None = None


class EntityRefModel(BaseModel):
    id: int
    name: str
    type: str
    description: str


class DedupeCandidateModel(BaseModel):
    id: int
    status: str
    created_at: str
    keep: EntityRefModel
    merge: list[EntityRefModel]


class DedupeScanRequest(BaseModel):
    admin_password: str


class EntitySearchResponse(BaseModel):
    entities: list[EntityRefModel]


class DedupeCandidateListResponse(BaseModel):
    candidates: list[DedupeCandidateModel]


class DedupeCandidateActionRequest(BaseModel):
    admin_password: str


class DedupeCandidateActionResponse(BaseModel):
    id: int
    status: str
    detail: str | None = None


class ManualMergeRequest(BaseModel):
    admin_password: str
    keep_id: int
    merge_id: int


class ManualMergeResponse(BaseModel):
    keep_id: int
    merge_id: int


class UndoableMergeModel(BaseModel):
    merged_entity: EntityRefModel
    keep: EntityRefModel


class UndoableMergesResponse(BaseModel):
    merges: list[UndoableMergeModel]


class UndoMergeRequest(BaseModel):
    admin_password: str


class UndoMergeResponse(BaseModel):
    entity_id: int
    restored: bool


class HostedLlmConfigModel(BaseModel):
    model: str
    max_tokens: int
    api_key_configured: bool


class GpuInfoModel(BaseModel):
    detected: bool
    name: str | None = None


class BackendConfigResponse(BaseModel):
    # What the running process actually loaded at startup - not necessarily
    # the same as saved_chat_backend if a save happened without a restart.
    active_chat_backend: str
    saved_chat_backend: str
    hosted_llm: HostedLlmConfigModel
    gpu: GpuInfoModel


class SetBackendConfigRequest(BaseModel):
    admin_password: str
    chat_backend: str
    hosted_llm_model: str | None = None
    hosted_llm_api_key: str | None = None
    hosted_llm_max_tokens: int | None = None


class SetBackendConfigResponse(BaseModel):
    saved_chat_backend: str
    restart_required: bool = True
