from __future__ import annotations

import math
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.pipeline.entity_extractor import CURATED_ENTITY_TYPES
from src.pipeline.mention_context import gather_mention_context
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaError
from src.wiki.summary import generate_entity_summary

router = APIRouter(tags=["wiki"])
logger = get_logger(__name__)

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


@router.get("/wiki/locations", response_class=HTMLResponse)
def wiki_locations(request: Request) -> HTMLResponse:
    entity_store = request.app.state.entity_store
    entities = entity_store.list_by_type("location")
    return _templates.TemplateResponse(
        request, "locations.html", {**_base_context(request), "entities": entities}
    )


@router.get("/wiki/graph", response_class=HTMLResponse)
def wiki_graph(request: Request) -> HTMLResponse:
    """A minimal, dependency-free node-link view: entities that participate
    in at least one relationship are laid out on a circle (no client-side JS
    or graph library needed) and connected by straight edges."""
    entity_store = request.app.state.entity_store
    relationships = entity_store.list_all_relationships()
    involved_ids = {r.entity_id for r in relationships} | {r.related_entity_id for r in relationships}
    entities = [e for e in entity_store.list_all() if e.id in involved_ids]

    center, radius = 300, 250
    positions = {
        entity.id: (
            center + radius * math.cos(2 * math.pi * i / len(entities)),
            center + radius * math.sin(2 * math.pi * i / len(entities)),
        )
        for i, entity in enumerate(entities)
    }

    nodes = [
        {"id": e.id, "name": e.name, "x": positions[e.id][0], "y": positions[e.id][1]} for e in entities
    ]
    edges = [
        {
            "x1": positions[r.entity_id][0],
            "y1": positions[r.entity_id][1],
            "x2": positions[r.related_entity_id][0],
            "y2": positions[r.related_entity_id][1],
        }
        for r in relationships
        if r.entity_id in positions and r.related_entity_id in positions
    ]

    return _templates.TemplateResponse(
        request, "graph.html", {**_base_context(request), "nodes": nodes, "edges": edges}
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
        vector_store = request.app.state.vector_store
        mention_context = gather_mention_context(mentions, vector_store)
        try:
            summary = generate_entity_summary(
                entity, len(mentions), mention_context, ollama_client, chat_model
            )
        except OllamaError as e:
            # The summary is a nice-to-have on top of the entity's stored
            # description (which the template already falls back to) - the
            # page should still render if Ollama is temporarily unreachable,
            # not 500 on every not-yet-summarized entity.
            logger.warning("Could not generate wiki summary for entity %d: %s", entity.id, e)
        else:
            entity_store.set_summary(entity.id, summary)
            entity = entity_store.get(entity.id)

    documents = sorted({_humanize_document_id(m.document_id) for m in mentions})

    relationships = [
        (related, rel.description)
        for rel in entity_store.get_relationships(entity.id)
        if (related := entity_store.get(rel.related_entity_id)) is not None
    ]
    # A faction's wiki page additionally functions as a roster: any related
    # entity whose relationship description reads as membership (not e.g.
    # "rival of" or "ally of") is shown as a member, on top of the general
    # relationships list every entity page already has.
    members = (
        [related for related, description in relationships if "member" in description.lower()]
        if entity.type == "faction"
        else []
    )

    return _templates.TemplateResponse(
        request,
        "entity.html",
        {
            **_base_context(request),
            "entity": entity,
            "mentions": mentions,
            "documents": documents,
            "relationships": relationships,
            "members": members,
        },
    )
