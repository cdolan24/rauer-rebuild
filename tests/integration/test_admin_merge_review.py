from __future__ import annotations

from tests.conftest import TEST_ADMIN_PASSWORD


def _add_entity(api_client, name: str, type_: str = "character", description: str = "desc") -> int:
    return api_client.app.state.entity_store.add_entity("doc1", name, type_, description)


def test_scan_persists_candidates_and_requires_admin_password(api_client):
    # Exact-name-after-normalization pairs short-circuit entity_deduper's LLM
    # confirmation step (see _confirm_pair), so this doesn't depend on the
    # FakeOllamaClient's canned, non-JSON chat response being parseable.
    keep_id = _add_entity(api_client, "Lady Justice")
    dup_id = _add_entity(api_client, "lady justice!")

    unauthorized = api_client.post("/api/admin/dedupe/scan", json={"admin_password": "wrong"})
    assert unauthorized.status_code == 401

    response = api_client.post("/api/admin/dedupe/scan", json={"admin_password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert len(candidates) == 1
    assert {candidates[0]["keep"]["id"], candidates[0]["merge"][0]["id"]} == {keep_id, dup_id}


def test_approve_candidate_merges_entities(api_client):
    keep_id = _add_entity(api_client, "Molly Squidpiddge")
    dup_id = _add_entity(api_client, "Molly-girl")
    api_client.app.state.entity_store.save_candidates([(keep_id, [dup_id])])
    candidate_id = api_client.app.state.entity_store.list_candidates()[0].id

    response = api_client.post(
        f"/api/admin/dedupe/candidates/{candidate_id}/approve",
        json={"admin_password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    merged = api_client.app.state.entity_store.get(dup_id)
    assert merged.merged_into_id == keep_id


def test_approve_stale_candidate_is_auto_rejected(api_client):
    keep_id = _add_entity(api_client, "Molly Squidpiddge")
    dup_id = _add_entity(api_client, "Molly-girl")
    other_id = _add_entity(api_client, "Someone Else")
    api_client.app.state.entity_store.save_candidates([(keep_id, [dup_id])])
    candidate_id = api_client.app.state.entity_store.list_candidates()[0].id
    # dup_id gets merged away via a different path before the candidate is reviewed
    api_client.app.state.entity_store.merge_entities(other_id, [dup_id])

    response = api_client.post(
        f"/api/admin/dedupe/candidates/{candidate_id}/approve",
        json={"admin_password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "stale" in response.json()["detail"].lower()


def test_reject_and_skip_candidate(api_client):
    keep_id = _add_entity(api_client, "A")
    dup_id = _add_entity(api_client, "A-variant")
    api_client.app.state.entity_store.save_candidates([(keep_id, [dup_id])])
    candidate_id = api_client.app.state.entity_store.list_candidates()[0].id

    response = api_client.post(
        f"/api/admin/dedupe/candidates/{candidate_id}/reject",
        json={"admin_password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert api_client.app.state.entity_store.get(dup_id).merged_into_id is None


def test_manual_merge(api_client):
    keep_id = _add_entity(api_client, "Perdita")
    other_id = _add_entity(api_client, "Nino")

    response = api_client.post(
        "/api/admin/merge",
        json={"admin_password": TEST_ADMIN_PASSWORD, "keep_id": keep_id, "merge_id": other_id},
    )

    assert response.status_code == 200
    assert api_client.app.state.entity_store.get(other_id).merged_into_id == keep_id


def test_manual_merge_rejects_self_merge(api_client):
    keep_id = _add_entity(api_client, "Perdita")

    response = api_client.post(
        "/api/admin/merge",
        json={"admin_password": TEST_ADMIN_PASSWORD, "keep_id": keep_id, "merge_id": keep_id},
    )

    assert response.status_code == 400


def test_undo_merge_round_trip(api_client):
    keep_id = _add_entity(api_client, "Perdita")
    other_id = _add_entity(api_client, "Nino")
    api_client.app.state.entity_store.merge_entities(keep_id, [other_id])

    undoable = api_client.get(
        "/api/admin/merges/undoable", params={"admin_password": TEST_ADMIN_PASSWORD}
    )
    assert undoable.status_code == 200
    assert any(m["merged_entity"]["id"] == other_id for m in undoable.json()["merges"])

    response = api_client.post(
        f"/api/admin/merges/{other_id}/undo", json={"admin_password": TEST_ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    assert api_client.app.state.entity_store.get(other_id).merged_into_id is None


def test_search_entities_by_name(api_client):
    _add_entity(api_client, "Lady Justice")
    _add_entity(api_client, "Perdita")

    response = api_client.get(
        "/api/admin/entities/search", params={"admin_password": TEST_ADMIN_PASSWORD, "query": "just"}
    )

    assert response.status_code == 200
    names = [e["name"] for e in response.json()["entities"]]
    assert names == ["Lady Justice"]


def test_undo_merge_rejects_ineligible_entity(api_client):
    entity_id = _add_entity(api_client, "Never Merged")

    response = api_client.post(
        f"/api/admin/merges/{entity_id}/undo", json={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 400
