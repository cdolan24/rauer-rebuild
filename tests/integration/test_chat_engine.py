from __future__ import annotations

from src.database.vector_store import VectorStore
from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk
from src.rag.chat_engine import NO_INFO_ANSWER, ChatEngine, ChatResponse
from src.rag.conversation_store import ConversationStore
from src.rag.retriever import Retriever


class CapturingOllamaClient:
    """Wraps a fake client but records every chat() call's message list."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.chat_calls: list[list[dict[str, str]]] = []

    def embed(self, model, text):
        return self._inner.embed(model, text)

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        self.chat_calls.append(messages)
        return self._inner.chat(model, messages, temperature, num_predict, keep_alive)

    def is_healthy(self):
        return self._inner.is_healthy()


def _seeded_vector_store(tmp_path, fake_ollama_client) -> VectorStore:
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    chunk = Chunk(
        chunk_id="c0",
        document_id="fellowship",
        text="Aragorn is a ranger who protects travelers on the road.",
        page_start=3,
        page_end=3,
    )
    embedded = EmbeddedChunk(chunk=chunk, embedding=fake_ollama_client.embed("fake-embed", chunk.text))
    vector_store.add_chunks([embedded])
    return vector_store


def test_grounded_answer_has_citations(tmp_path, fake_ollama_client):
    vector_store = _seeded_vector_store(tmp_path, fake_ollama_client)
    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")
    engine = ChatEngine(
        retriever, fake_ollama_client, ConversationStore(), chat_model="fake-chat", min_score=0.0
    )

    response = engine.ask("conv-1", "Who is Aragorn?")

    assert response.answer != NO_INFO_ANSWER
    assert len(response.citations) == 1
    assert response.citations[0].document_id == "fellowship"
    assert response.citations[0].page_start == 3


def test_no_relevant_content_falls_back(tmp_path, fake_ollama_client):
    empty_vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    retriever = Retriever(empty_vector_store, fake_ollama_client, embedding_model="fake-embed")
    engine = ChatEngine(retriever, fake_ollama_client, ConversationStore(), chat_model="fake-chat")

    response = engine.ask("conv-1", "Who is Aragorn?")

    assert response.answer == NO_INFO_ANSWER
    assert response.citations == []


def test_multi_turn_conversation_passes_prior_history(tmp_path, fake_ollama_client):
    vector_store = _seeded_vector_store(tmp_path, fake_ollama_client)
    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")
    capturing_client = CapturingOllamaClient(fake_ollama_client)
    engine = ChatEngine(
        retriever, capturing_client, ConversationStore(), chat_model="fake-chat", min_score=0.0
    )

    engine.ask("conv-1", "Who is Aragorn?")
    engine.ask("conv-1", "Where does he protect travelers?")

    assert len(capturing_client.chat_calls) == 2
    second_call_messages = capturing_client.chat_calls[1]
    contents = [m["content"] for m in second_call_messages]
    assert any("Who is Aragorn?" in c for c in contents)


def test_ask_stream_yields_fragments_then_final_response_with_citations(tmp_path, fake_ollama_client):
    vector_store = _seeded_vector_store(tmp_path, fake_ollama_client)
    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")
    engine = ChatEngine(
        retriever, fake_ollama_client, ConversationStore(), chat_model="fake-chat", min_score=0.0
    )

    events = list(engine.ask_stream("conv-1", "Who is Aragorn?"))

    *fragments, final = events
    assert all(isinstance(f, str) for f in fragments)
    assert len(fragments) > 1  # actually streamed, not one giant chunk
    assert "".join(fragments) == final.answer
    assert len(final.citations) == 1
    assert final.citations[0].document_id == "fellowship"


def test_ask_stream_no_relevant_content_yields_single_fallback_fragment(tmp_path, fake_ollama_client):
    empty_vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    retriever = Retriever(empty_vector_store, fake_ollama_client, embedding_model="fake-embed")
    engine = ChatEngine(retriever, fake_ollama_client, ConversationStore(), chat_model="fake-chat")

    events = list(engine.ask_stream("conv-1", "Who is Aragorn?"))

    assert events == [NO_INFO_ANSWER, ChatResponse(answer=NO_INFO_ANSWER, citations=[])]


def test_ask_stream_updates_conversation_history(tmp_path, fake_ollama_client):
    vector_store = _seeded_vector_store(tmp_path, fake_ollama_client)
    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")
    conversation_store = ConversationStore()
    engine = ChatEngine(
        retriever, fake_ollama_client, conversation_store, chat_model="fake-chat", min_score=0.0
    )

    list(engine.ask_stream("conv-1", "Who is Aragorn?"))

    history = conversation_store.get_history("conv-1")
    assert len(history) == 1
    assert history[0].question == "Who is Aragorn?"
