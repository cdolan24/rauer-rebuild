from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.pipeline.entity_extractor import CURATED_ENTITY_TYPES
from src.wiki.summary import generate_entity_summary

router = APIRouter(tags=["wiki"])

_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _entity_color_class(type_: str) -> str:
    """CSS class for an entity's type button - a shared neutral fallback for
    any surviving dynamic tag, since there's no color assigned ahead of time
    for a tag that didn't exist when this was written."""
    return f"type-{type_}" if type_ in CURATED_ENTITY_TYPES else "type-other"


_templates.env.filters["entity_color_class"] = _entity_color_class


def _category_counts(entity_store) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entity in entity_store.list_all():
        counts[entity.type] = counts.get(entity.type, 0) + 1
    return counts


def _humanize_document_id(document_id: str) -> str:
    return document_id.replace("_", " ").replace("-", " ").title()


def _base_context(request: Request) -> dict:
    """Context every wiki page needs: sidebar category counts and the
    frontend's actual (possibly cross-origin) address for nav links."""
    entity_store = request.app.state.entity_store
    return {
        "category_counts": _category_counts(entity_store),
        "frontend_url": request.app.state.config.frontend.public_url,
    }


@router.get("/wiki", response_class=HTMLResponse)
def wiki_index(request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    registry = request.app.state.registry
    by_type: dict[str, list] = {}
    for entity in entity_store.list_all():
        by_type.setdefault(entity.type, []).append(entity)
    total_documents = len([r for r in registry.list_all() if r.status == "processed"])
    return _templates.TemplateResponse(
        request,
        "index.html",
        {
            **_base_context(request),
            "by_type": by_type,
            "total_entities": sum(len(entities) for entities in by_type.values()),
            "total_documents": total_documents,
        },
    )


@router.get("/wiki/category/{type_}", response_class=HTMLResponse)
def wiki_category(type_: str, request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    entities = entity_store.list_by_type(type_)
    return _templates.TemplateResponse(
        request, "category.html", {**_base_context(request), "type": type_, "entities": entities}
    )


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

    documents = sorted({_humanize_document_id(m.document_id) for m in mentions})

    return _templates.TemplateResponse(
        request,
        "entity.html",
        {**_base_context(request), "entity": entity, "mentions": mentions, "documents": documents},
    )
