from __future__ import annotations

from src.database.entity_store import EntityMention

# api_client fixture comes from tests/conftest.py


def test_wiki_index_empty(api_client):
    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert "No entities extracted yet." in response.text


def test_wiki_chat_link_points_to_frontend_not_relative_root(api_client):
    response = api_client.get("/wiki")

    assert response.status_code == 200
    # The wiki is served by the backend; chat lives on a different origin
    # (the frontend). A relative href="/" would 404 against the backend.
    assert 'href="http://localhost:7860">Chat</a>' in response.text


def test_wiki_index_lists_categories_with_counts(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_entity("doc1", "Bree", "location", "A frontier town.")

    response = api_client.get("/wiki")

    assert response.status_code == 200
    # The landing page shows category tiles, not individual entity names -
    # browsing entities happens on the category page.
    assert "Lady Justice" not in response.text
    assert '/wiki/category/character' in response.text
    assert '/wiki/category/location' in response.text
    assert "Characters (1)" in response.text
    assert "Locations (1)" in response.text


def test_wiki_index_shows_entity_and_document_stats(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_entity("doc1", "Bree", "location", "A frontier town.")
    api_client.app.state.registry.mark_processed("doc1", "doc1", "doc1.pdf", 5, 1)

    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert '<strong>2</strong><span>Entities</span>' in response.text
    assert '<strong>1</strong><span>Documents</span>' in response.text


def test_wiki_category_lists_matching_entities(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.add_entity("doc1", "Bree", "location", "A frontier town.")

    response = api_client.get("/wiki/category/character")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    assert "Bree" not in response.text


def test_wiki_category_entities_colored_by_type(api_client):
    store = api_client.app.state.entity_store
    store.add_entity("doc1", "Nathan Caroland", "real-person", "Author of the M1E Core")

    response = api_client.get("/wiki/category/real-person")

    assert response.status_code == 200
    assert 'class="wiki-btn type-real-person"' in response.text


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


def test_wiki_entity_page_falls_back_to_description_when_summary_generation_fails(
    unhealthy_api_client,
):
    """Regression test: the page should still render using the entity's
    stored description if Ollama is unreachable when a not-yet-summarized
    entity is first viewed, rather than 500ing on an otherwise-avoidable
    dependency (the template already falls back to the description)."""
    store = unhealthy_api_client.app.state.entity_store
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")

    response = unhealthy_api_client.get(f"/wiki/entity/{entity_id}")

    assert response.status_code == 200
    assert "A Guild enforcer." in response.text
    assert store.get(entity_id).summary is None
