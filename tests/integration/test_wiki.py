from __future__ import annotations

from src.database.entity_store import EntityMention

# api_client fixture comes from tests/conftest.py


def test_wiki_index_empty(api_client):
    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert "No entities extracted yet." in response.text


def test_wiki_index_lists_entities_by_type(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_entity("doc1", "Bree", "location", "A frontier town.")

    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    assert "Bree" in response.text
    assert '/wiki/category/character' in response.text
    assert '/wiki/category/location' in response.text


def test_wiki_category_lists_matching_entities(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_entity("doc1", "Bree", "location", "A frontier town.")

    response = api_client.get("/wiki/category/character")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    assert "Bree" not in response.text


def test_wiki_category_empty(api_client):
    response = api_client.get("/wiki/category/faction")

    assert response.status_code == 200
    assert "No entities found for this category." in response.text


def test_wiki_entity_page_generates_and_caches_summary(api_client):
    store = api_client.app.state.entity_store
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_mentions(
        [EntityMention(entity_id=entity_id, chunk_id="c0", document_id="doc1", page_start=30, page_end=30)]
    )

    response = api_client.get(f"/wiki/entity/{entity_id}")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    assert "character" in response.text
    assert "doc1, p. 30" in response.text
    assert 'href="/api/documents/doc1/pdf#page=30"' in response.text

    # Summary should now be cached on the entity row.
    entity = store.get(entity_id)
    assert entity.summary is not None


def test_wiki_entity_not_found(api_client):
    response = api_client.get("/wiki/entity/999999")
    assert response.status_code == 404
