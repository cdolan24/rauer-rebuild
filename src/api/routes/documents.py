from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from src.api.schemas import DocumentContentResponse, DocumentListResponse, DocumentSummary, UploadResponse
from src.pipeline.ingest import ingest_pdf
from src.utils.auth import check_admin_password

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(request: Request) -> DocumentListResponse:
    registry = request.app.state.registry
    records = registry.list_all()
    return DocumentListResponse(
        documents=[
            DocumentSummary(
                id=r.document_id,
                title=r.title,
                status=r.status,
                pages=r.page_count,
                chunks=r.chunk_count,
            )
            for r in records
        ]
    )


@router.get("/documents/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, request: Request) -> DocumentSummary:
    registry = request.app.state.registry
    record = registry.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")
    return DocumentSummary(
        id=record.document_id,
        title=record.title,
        status=record.status,
        pages=record.page_count,
        chunks=record.chunk_count,
    )


@router.get("/documents/{document_id}/content", response_model=DocumentContentResponse)
def get_document_content(document_id: str, request: Request) -> DocumentContentResponse:
    registry = request.app.state.registry
    record = registry.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    processed_dir = request.app.state.config.paths.processed_dir
    content_path = Path(processed_dir) / f"{document_id}.txt"
    if not content_path.exists():
        raise HTTPException(status_code=404, detail=f"No processed content for '{document_id}' yet")

    return DocumentContentResponse(
        id=record.document_id,
        title=record.title,
        content=content_path.read_text(encoding="utf-8"),
    )


@router.get("/documents/{document_id}/pdf")
def get_document_pdf(document_id: str, request: Request) -> FileResponse:
    registry = request.app.state.registry
    record = registry.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

    pdf_path = Path(record.source_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Original PDF for '{document_id}' not found on disk")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
        content_disposition_type="inline",
    )


@router.post("/documents/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    request: Request,
    background_tasks: BackgroundTasks,
    admin_password: str = Form(...),
) -> UploadResponse:
    config = request.app.state.config
    check_admin_password(
        request.app.state.admin_rate_limiter, request.client.host, config.admin_password, admin_password
    )

    registry = request.app.state.registry
    entity_store = request.app.state.entity_store
    vector_store = request.app.state.vector_store
    ollama_client = request.app.state.ollama_client

    data_dir = Path(config.paths.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    dest_path = data_dir / file.filename
    contents = await file.read()
    dest_path.write_bytes(contents)

    document_id = dest_path.stem
    registry.mark_pending(document_id, dest_path.stem, str(dest_path))

    background_tasks.add_task(
        ingest_pdf,
        dest_path,
        registry,
        vector_store,
        ollama_client,
        config.ollama.embedding_model,
        config.chunking.chunk_size,
        config.chunking.chunk_overlap,
        config.paths.processed_dir,
        entity_store=entity_store,
        chat_model=config.ollama.chat_model,
    )

    return UploadResponse(document_id=document_id, status="pending")
