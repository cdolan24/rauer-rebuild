from __future__ import annotations

from src.database.entity_store import Entity
from src.wiki.summary import generate_entity_summary


class CapturingOllamaClient:
    """Records the outgoing prompt and returns a fixed response, so tests can
    assert on what the summary generator actually sends to the model."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_messages: list[dict[str, str]] | None = None

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        self.last_messages = messages
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


def _entity(name="Lady Justice", type_="character", description="A Guild enforcer."):
    return Entity(id=1, document_id="doc1", name=name, type=type_, description=description)


def test_generate_entity_summary_includes_mention_context_in_prompt():
    client = CapturingOllamaClient("A long article about Lady Justice.")

    summary = generate_entity_summary(
        _entity(), mention_count=3, mention_context="She drew her revolver in Bree.",
        ollama_client=client, chat_model="fake-chat",
    )

    assert summary == "A long article about Lady Justice."
    prompt = client.last_messages[-1]["content"]
    assert "She drew her revolver in Bree." in prompt
    assert "A Guild enforcer." in prompt  # known facts still included alongside passages


def test_generate_entity_summary_handles_empty_mention_context():
    client = CapturingOllamaClient("A short article based on known facts alone.")

    summary = generate_entity_summary(
        _entity(), mention_count=0, mention_context="",
        ollama_client=client, chat_model="fake-chat",
    )

    assert summary == "A short article based on known facts alone."
    prompt = client.last_messages[-1]["content"]
    assert "(no passages available)" in prompt
