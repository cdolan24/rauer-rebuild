from __future__ import annotations

from src.database.vector_store import SearchResult
from src.rag.conversation_store import ConversationTurn
from src.rag.prompt_builder import build_messages


def _chunk(doc_id="doc1", page_start=1, page_end=1, text="Aragorn is a ranger.") -> SearchResult:
    return SearchResult(
        chunk_id="c0", document_id=doc_id, text=text, page_start=page_start, page_end=page_end, score=0.9
    )


def test_build_messages_includes_system_prompt_first():
    messages = build_messages("Who is Aragorn?", [_chunk()], history=[])

    assert messages[0]["role"] == "system"
    assert len(messages[0]["content"]) > 0


def test_build_messages_includes_context_and_question():
    messages = build_messages("Who is Aragorn?", [_chunk()], history=[])

    final_message = messages[-1]
    assert final_message["role"] == "user"
    assert "Aragorn is a ranger." in final_message["content"]
    assert "doc1" in final_message["content"]
    assert "Who is Aragorn?" in final_message["content"]


def test_build_messages_includes_prior_history_in_order():
    history = [ConversationTurn(question="What is Bree?", answer="A town.")]

    messages = build_messages("Who is Aragorn?", [_chunk()], history=history)

    assert messages[1] == {"role": "user", "content": "What is Bree?"}
    assert messages[2] == {"role": "assistant", "content": "A town."}
    assert messages[-1]["content"].endswith("Who is Aragorn?")


def test_build_messages_formats_page_range():
    messages = build_messages(
        "Q", [_chunk(page_start=3, page_end=5)], history=[]
    )

    assert "pp. 3-5" in messages[-1]["content"]
