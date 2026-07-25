from __future__ import annotations

import math
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.pipeline.entity_extractor import CURATED_ENTITY_TYPES
from src.pipeline.mention_context import gather_mention_context
from src.utils.chat_backend import ChatBackendError
from src.utils.logging import get_logger
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


def _neighborhood_layout(entity, related_entities: list) -> tuple[list[dict], list[dict]]:
    """Position `entity` at the SVG center and its direct neighbors evenly
    around a fixed-radius circle - a small subgraph like this (one focus
    entity plus its immediate relationships) is legible on a plain circle
    without any force-directed layout; that's only worth the effort at the
    whole-graph scale this endpoint deliberately never renders."""
    center, radius = 300, 250
    positions = {entity.id: (center, center)}
    count = len(related_entities) or 1
    for i, related in enumerate(related_entities):
        positions[related.id] = (
            center + radius * math.cos(2 * math.pi * i / count),
            center + radius * math.sin(2 * math.pi * i / count),
        )
    nodes = [
        {"id": e.id, "name": e.name, "type": e.type, "x": positions[e.id][0], "y": positions[e.id][1]}
        for e in [entity, *related_entities]
    ]
    return nodes, positions


@router.get("/wiki/graph", response_class=HTMLResponse)
def wiki_graph(request: Request) -> HTMLResponse:
    """The graph page renders empty by default - a search box and no nodes
    or edges - rather than laying out the whole entity/relationship graph
    at once (illegible at the real ~900-entity/~4,000-relationship scale).
    A specific entity's neighborhood is loaded on demand client-side via
    /wiki/graph/data, seeded by search, node click, or a ?focus= deep link;
    this route stays a dumb shell that doesn't need to know about any of
    that - it's read from window.location in the page's own JS."""
    return _templates.TemplateResponse(request, "graph.html", _base_context(request))


@router.get("/wiki/graph/data")
def wiki_graph_data(entity_id: int, request: Request) -> JSONResponse:
    """JSON neighborhood for one entity: itself plus its direct (depth-1)
    relationships, in the {nodes, edges} shape graph.html already expects."""
    entity_store = request.app.state.entity_store
    entity = entity_store.get(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")

    relationships = entity_store.get_relationships(entity.id)
    related_entities = [
        related for r in relationships if (related := entity_store.get(r.related_entity_id)) is not None
    ]

    nodes, positions = _neighborhood_layout(entity, related_entities)
    edges = [
        {
            "source_id": r.entity_id,
            "target_id": r.related_entity_id,
            "x1": positions[r.entity_id][0],
            "y1": positions[r.entity_id][1],
            "x2": positions[r.related_entity_id][0],
            "y2": positions[r.related_entity_id][1],
        }
        for r in relationships
        if r.related_entity_id in positions
    ]

    return JSONResponse({"nodes": nodes, "edges": edges})


@router.get("/wiki/graph/search")
def wiki_graph_search(q: str, request: Request) -> JSONResponse:
    """Small {id, name} match list for the graph page's search box - reuses
    the same case-insensitive substring search the admin manual-merge picker
    already uses, so the client never has to hold the full ~900-entity name
    index just to find one starting point."""
    entity_store = request.app.state.entity_store
    matches = entity_store.search_by_name(q) if q.strip() else []
    return JSONResponse([{"id": e.id, "name": e.name} for e in matches])


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
        chat_backend = request.app.state.chat_backend
        vector_store = request.app.state.vector_store
        mention_context = gather_mention_context(mentions, vector_store)
        try:
            summary = generate_entity_summary(entity, len(mentions), mention_context, chat_backend)
        except ChatBackendError as e:
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
