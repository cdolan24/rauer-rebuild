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


def test_wiki_locations_page_lists_only_locations(api_client):
    store = api_client.app.state.entity_store
    bree_id = store.add_entity("doc1", "Bree", "location", "A frontier town.")
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")

    response = api_client.get("/wiki/locations")

    assert response.status_code == 200
    assert "Bree" in response.text
    assert "Lady Justice" not in response.text
    assert f'href="/wiki/entity/{bree_id}"' in response.text


def test_wiki_locations_page_empty(api_client):
    response = api_client.get("/wiki/locations")

    assert response.status_code == 200
    assert "No locations found." in response.text


def test_wiki_sidebar_links_to_locations_page(api_client):
    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert 'href="/wiki/locations"' in response.text


def test_wiki_graph_page_shows_related_entities(api_client):
    store = api_client.app.state.entity_store
    justice_id = store.add_entity("doc1", "Lady Justice", "character", "desc")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "desc")
    store.add_entity("doc1", "Unrelated Entity", "character", "desc")  # no relationships
    store.add_relationship(justice_id, guild_id, "member of")

    response = api_client.get("/wiki/graph")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    assert "The Guild" in response.text
    assert "Unrelated Entity" not in response.text  # not part of any relationship
    assert f'href="/wiki/entity/{justice_id}"' in response.text


def test_wiki_graph_page_empty_state(api_client):
    response = api_client.get("/wiki/graph")

    assert response.status_code == 200
    assert "No relationships have been extracted yet." in response.text


def test_wiki_sidebar_links_to_graph_page(api_client):
    response = api_client.get("/wiki")

    assert response.status_code == 200
    assert 'href="/wiki/graph"' in response.text


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


def test_wiki_entity_page_lists_relationships(api_client):
    store = api_client.app.state.entity_store
    justice_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "A shadowy organization.")
    store.add_relationship(justice_id, guild_id, "member of")

    response = api_client.get(f"/wiki/entity/{justice_id}")

    assert response.status_code == 200
    assert "The Guild" in response.text
    assert "member of" in response.text
    assert f'href="/wiki/entity/{guild_id}"' in response.text


def test_wiki_entity_page_no_relationships_renders_empty_state(api_client):
    store = api_client.app.state.entity_store
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")

    response = api_client.get(f"/wiki/entity/{entity_id}")

    assert response.status_code == 200
    assert "No recorded relationships." in response.text


def test_wiki_faction_page_lists_members(api_client):
    store = api_client.app.state.entity_store
    guild_id = store.add_entity("doc1", "The Guild", "faction", "A shadowy organization.")
    justice_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    rival_id = store.add_entity("doc1", "Rasputina", "character", "An ice witch.")
    store.add_relationship(guild_id, justice_id, "member of")
    store.add_relationship(guild_id, rival_id, "rival of")

    response = api_client.get(f"/wiki/entity/{guild_id}")

    assert response.status_code == 200
    assert "Lady Justice" in response.text
    # Rasputina is related (a rival), but not a member - shouldn't be listed
    # under Members even though she appears under the general Relationships list.
    members_section = response.text.split("<h2>Members</h2>")[1].split("<h2>Relationships</h2>")[0]
    assert "Lady Justice" in members_section
    assert "Rasputina" not in members_section


def test_wiki_faction_page_no_members_renders_empty_state(api_client):
    store = api_client.app.state.entity_store
    guild_id = store.add_entity("doc1", "The Guild", "faction", "A shadowy organization.")

    response = api_client.get(f"/wiki/entity/{guild_id}")

    assert response.status_code == 200
    assert "No recorded members." in response.text


def test_wiki_non_faction_entity_page_has_no_members_section(api_client):
    store = api_client.app.state.entity_store
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")

    response = api_client.get(f"/wiki/entity/{entity_id}")

    assert response.status_code == 200
    assert "<h2>Members</h2>" not in response.text


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
