from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.wiki.summary import generate_entity_summary

router = APIRouter(tags=["wiki"])

_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/wiki", response_class=HTMLResponse)
def wiki_index(request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    by_type: dict[str, list] = {}
    for entity in entity_store.list_all():
        by_type.setdefault(entity.type, []).append(entity)
    return _templates.TemplateResponse(request, "index.html", {"by_type": by_type})


@router.get("/wiki/category/{type_}", response_class=HTMLResponse)
def wiki_category(type_: str, request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    entities = entity_store.list_by_type(type_)
    return _templates.TemplateResponse(request, "category.html", {"type": type_, "entities": entities})


@router.get("/wiki/entity/{entity_id}", response_class=HTMLResponse)
def wiki_entity(entity_id: int, request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    entity = entity_store.get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    mentions = entity_store.get_mentions(entity.id)

    if not entity.summary:
        ollama_client = request.app.state.ollama_client
        chat_model = request.app.state.config.ollama.chat_model
        summary = generate_entity_summary(entity, len(mentions), ollama_client, chat_model)
        entity_store.set_summary(entity.id, summary)
        entity = entity_store.get(entity.id)

    return _templates.TemplateResponse(request, "entity.html", {"entity": entity, "mentions": mentions})
