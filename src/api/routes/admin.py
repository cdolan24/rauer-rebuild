from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    AdminQueryRequest,
    AdminQueryResponse,
    BackendConfigResponse,
    DedupeCandidateActionRequest,
    DedupeCandidateActionResponse,
    DedupeCandidateListResponse,
    DedupeCandidateModel,
    DedupeScanRequest,
    EntityRefModel,
    EntitySearchResponse,
    GpuInfoModel,
    HostedLlmConfigModel,
    ManualMergeRequest,
    ManualMergeResponse,
    SetBackendConfigRequest,
    SetBackendConfigResponse,
    UndoableMergeModel,
    UndoableMergesResponse,
    UndoMergeRequest,
    UndoMergeResponse,
)
from src.database.entity_store import Entity
from src.pipeline.entity_deduper import find_duplicate_groups
from src.utils.auth import check_admin_password, get_client_ip
from src.utils.config import get_config_path, load_config
from src.utils.config_writer import update_chat_backend_config
from src.utils.gpu_detect import detect_gpu

router = APIRouter(tags=["admin"])


def _entity_ref(entity: Entity) -> EntityRefModel:
    return EntityRefModel(id=entity.id, name=entity.name, type=entity.type, description=entity.description)


def _check_admin(request: Request, admin_password: str) -> None:
    config = request.app.state.config
    check_admin_password(
        request.app.state.admin_rate_limiter, get_client_ip(request), config.admin_password, admin_password
    )


@router.post("/admin/query", response_model=AdminQueryResponse)
def run_query(payload: AdminQueryRequest, request: Request) -> AdminQueryResponse:
    """Run arbitrary SQL against the application database. Gated behind the
    same admin password as PDF upload - this is deliberately unrestricted
    (no statement-type filtering): "direct database access" means direct
    access, with the admin password as the only trust boundary."""
    _check_admin(request, payload.admin_password)

    conn = sqlite3.connect(request.app.state.config.data_storage_path)
    try:
        cursor = conn.execute(payload.sql)
        if cursor.description is not None:
            columns = [col[0] for col in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]
            conn.commit()
            return AdminQueryResponse(columns=columns, rows=rows)
        conn.commit()
        return AdminQueryResponse(columns=[], rows=[], rows_affected=cursor.rowcount)
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {e}") from e
    finally:
        conn.close()


def _candidate_model(entity_store, candidate) -> DedupeCandidateModel | None:
    """Resolve a stored candidate's ids to entity refs for display. Returns
    None if any referenced entity is gone entirely (not just merged away) -
    that candidate is too stale to show at all."""
    keep = entity_store.get(candidate.keep_id)
    merge_entities = [entity_store.get(i) for i in candidate.merge_ids]
    if keep is None or any(e is None for e in merge_entities):
        return None
    return DedupeCandidateModel(
        id=candidate.id,
        status=candidate.status,
        created_at=candidate.created_at,
        keep=_entity_ref(keep),
        merge=[_entity_ref(e) for e in merge_entities],
    )


@router.post("/admin/dedupe/scan", response_model=DedupeCandidateListResponse)
def scan_for_duplicates(payload: DedupeScanRequest, request: Request) -> DedupeCandidateListResponse:
    """Run the automated dedupe candidate-finder and persist the results for
    one-at-a-time review, replacing any still-pending candidates from a
    previous scan (already-reviewed candidates are kept as history)."""
    _check_admin(request, payload.admin_password)

    entity_store = request.app.state.entity_store
    chat_backend = request.app.state.chat_backend

    entities = entity_store.list_all()
    groups = find_duplicate_groups(entities, chat_backend)
    entity_store.save_candidates([(g.keep_id, g.merge_ids) for g in groups])

    candidates = [_candidate_model(entity_store, c) for c in entity_store.list_candidates(status="pending")]
    return DedupeCandidateListResponse(candidates=[c for c in candidates if c is not None])


@router.get("/admin/dedupe/candidates", response_model=DedupeCandidateListResponse)
def list_dedupe_candidates(
    request: Request, admin_password: str, status: str | None = None
) -> DedupeCandidateListResponse:
    _check_admin(request, admin_password)
    entity_store = request.app.state.entity_store
    candidates = [_candidate_model(entity_store, c) for c in entity_store.list_candidates(status=status)]
    return DedupeCandidateListResponse(candidates=[c for c in candidates if c is not None])


def _get_candidate_or_404(entity_store, candidate_id: int):
    candidate = entity_store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"Dedupe candidate {candidate_id} not found")
    return candidate


def _validate_mergeable(entity_store, keep_id: int, merge_ids: list[int]) -> str | None:
    """Returns None if every referenced entity still exists and is not
    already merged away, otherwise a human-readable reason it's stale."""
    keep = entity_store.get(keep_id)
    if keep is None:
        return f"Entity {keep_id} no longer exists"
    if keep.merged_into_id is not None:
        return f"Entity {keep_id} has itself since been merged into {keep.merged_into_id}"
    for merge_id in merge_ids:
        merge_entity = entity_store.get(merge_id)
        if merge_entity is None:
            return f"Entity {merge_id} no longer exists"
        if merge_entity.merged_into_id is not None:
            return f"Entity {merge_id} has already been merged into {merge_entity.merged_into_id}"
    return None


@router.post("/admin/dedupe/candidates/{candidate_id}/approve", response_model=DedupeCandidateActionResponse)
def approve_dedupe_candidate(
    candidate_id: int, payload: DedupeCandidateActionRequest, request: Request
) -> DedupeCandidateActionResponse:
    _check_admin(request, payload.admin_password)
    entity_store = request.app.state.entity_store
    candidate = _get_candidate_or_404(entity_store, candidate_id)

    stale_reason = _validate_mergeable(entity_store, candidate.keep_id, candidate.merge_ids)
    if stale_reason is not None:
        entity_store.update_candidate_status(candidate_id, "rejected")
        return DedupeCandidateActionResponse(
            id=candidate_id, status="rejected", detail=f"Skipped stale candidate: {stale_reason}"
        )

    entity_store.merge_entities(candidate.keep_id, candidate.merge_ids)
    entity_store.update_candidate_status(candidate_id, "approved")
    return DedupeCandidateActionResponse(id=candidate_id, status="approved")


@router.post("/admin/dedupe/candidates/{candidate_id}/reject", response_model=DedupeCandidateActionResponse)
def reject_dedupe_candidate(
    candidate_id: int, payload: DedupeCandidateActionRequest, request: Request
) -> DedupeCandidateActionResponse:
    _check_admin(request, payload.admin_password)
    entity_store = request.app.state.entity_store
    _get_candidate_or_404(entity_store, candidate_id)
    entity_store.update_candidate_status(candidate_id, "rejected")
    return DedupeCandidateActionResponse(id=candidate_id, status="rejected")


@router.post("/admin/dedupe/candidates/{candidate_id}/skip", response_model=DedupeCandidateActionResponse)
def skip_dedupe_candidate(
    candidate_id: int, payload: DedupeCandidateActionRequest, request: Request
) -> DedupeCandidateActionResponse:
    _check_admin(request, payload.admin_password)
    entity_store = request.app.state.entity_store
    _get_candidate_or_404(entity_store, candidate_id)
    entity_store.update_candidate_status(candidate_id, "skipped")
    return DedupeCandidateActionResponse(id=candidate_id, status="skipped")


@router.get("/admin/entities/search", response_model=EntitySearchResponse)
def search_entities(request: Request, admin_password: str, query: str = "") -> EntitySearchResponse:
    """Backs the manual-merge picker - narrows the full entity store down to
    a pickable few by name substring, rather than listing ~1000 entities."""
    _check_admin(request, admin_password)
    entity_store = request.app.state.entity_store
    entities = entity_store.search_by_name(query)
    return EntitySearchResponse(entities=[_entity_ref(e) for e in entities])


@router.post("/admin/merge", response_model=ManualMergeResponse)
def manual_merge(payload: ManualMergeRequest, request: Request) -> ManualMergeResponse:
    """Merge two arbitrary entities, independent of the automated dedupe
    scan, using the same reversible merge path."""
    _check_admin(request, payload.admin_password)
    entity_store = request.app.state.entity_store

    if payload.keep_id == payload.merge_id:
        raise HTTPException(status_code=400, detail="Cannot merge an entity into itself")
    stale_reason = _validate_mergeable(entity_store, payload.keep_id, [payload.merge_id])
    if stale_reason is not None:
        raise HTTPException(status_code=400, detail=stale_reason)

    entity_store.merge_entities(payload.keep_id, [payload.merge_id])
    return ManualMergeResponse(keep_id=payload.keep_id, merge_id=payload.merge_id)


@router.get("/admin/merges/undoable", response_model=UndoableMergesResponse)
def list_undoable_merges(request: Request, admin_password: str) -> UndoableMergesResponse:
    _check_admin(request, admin_password)
    entity_store = request.app.state.entity_store
    merges = []
    for merged_entity in entity_store.list_merged_away():
        if not entity_store.can_undo_merge(merged_entity.id):
            continue
        keep = entity_store.get(merged_entity.merged_into_id)
        if keep is None:
            continue
        merges.append(UndoableMergeModel(merged_entity=_entity_ref(merged_entity), keep=_entity_ref(keep)))
    return UndoableMergesResponse(merges=merges)


@router.post("/admin/merges/{entity_id}/undo", response_model=UndoMergeResponse)
def undo_merge(entity_id: int, payload: UndoMergeRequest, request: Request) -> UndoMergeResponse:
    _check_admin(request, payload.admin_password)
    entity_store = request.app.state.entity_store
    if not entity_store.can_undo_merge(entity_id):
        raise HTTPException(
            status_code=400,
            detail=f"Merge for entity {entity_id} cannot be undone (not merged, or its keeper "
            "has itself been merged elsewhere since)",
        )
    entity_store.undo_merge(entity_id)
    return UndoMergeResponse(entity_id=entity_id, restored=True)


@router.get("/admin/backend-config", response_model=BackendConfigResponse)
def get_backend_config(request: Request, admin_password: str) -> BackendConfigResponse:
    """Reports both the backend the running process actually loaded at
    startup (`active_chat_backend`) and whatever is currently saved on disk
    (`saved_chat_backend`) - these can differ if an admin has saved a new
    choice but not yet restarted, which is exactly the state a restart
    reminder needs to be visible about."""
    _check_admin(request, admin_password)
    active_config = request.app.state.config
    saved_config = load_config(get_config_path())
    gpu = detect_gpu()

    return BackendConfigResponse(
        active_chat_backend=active_config.chat_backend,
        saved_chat_backend=saved_config.chat_backend,
        hosted_llm=HostedLlmConfigModel(
            model=saved_config.hosted_llm.model,
            max_tokens=saved_config.hosted_llm.max_tokens,
            api_key_configured=bool(saved_config.hosted_llm.api_key),
        ),
        gpu=GpuInfoModel(detected=gpu.detected, name=gpu.name),
    )


@router.post("/admin/backend-config", response_model=SetBackendConfigResponse)
def set_backend_config(payload: SetBackendConfigRequest, request: Request) -> SetBackendConfigResponse:
    _check_admin(request, payload.admin_password)
    if payload.chat_backend not in ("ollama", "hosted_api"):
        raise HTTPException(
            status_code=400, detail=f"Unknown chat_backend '{payload.chat_backend}' (expected 'ollama' or 'hosted_api')"
        )

    update_chat_backend_config(
        get_config_path(),
        chat_backend=payload.chat_backend,
        hosted_llm_model=payload.hosted_llm_model,
        hosted_llm_api_key=payload.hosted_llm_api_key,
        hosted_llm_max_tokens=payload.hosted_llm_max_tokens,
    )
    return SetBackendConfigResponse(saved_chat_backend=payload.chat_backend, restart_required=True)
