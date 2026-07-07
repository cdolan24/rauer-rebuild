from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from src.rag.conversation_store import ConversationStore
from src.rag.prompt_builder import build_messages
from src.rag.retriever import Retriever
from src.utils.ollama_client import OllamaClient

NO_INFO_ANSWER = "I don't have information about that in the documents I've processed."


@dataclass
class Citation:
    document_id: str
    page_start: int
    page_end: int
    chunk_id: str
    score: float


@dataclass
class ChatResponse:
    answer: str
    citations: list[Citation]


class ChatEngine:
    """Retrieve-then-generate RAG flow: embed question, search vector store,
    build a prompt from the retrieved chunks, and generate an answer with a
    local Ollama chat model. Citations are attached from chunk metadata, not
    trusted to the LLM."""

    def __init__(
        self,
        retriever: Retriever,
        ollama_client: OllamaClient,
        conversation_store: ConversationStore,
        chat_model: str,
        top_k: int = 5,
        min_score: float = 0.55,
        num_predict: int | None = None,
        keep_alive: str | None = None,
    ) -> None:
        self._retriever = retriever
        self._ollama_client = ollama_client
        self._conversation_store = conversation_store
        self._chat_model = chat_model
        self._top_k = top_k
        self._min_score = min_score
        self._num_predict = num_predict
        self._keep_alive = keep_alive

    def ask(self, conversation_id: str, question: str) -> ChatResponse:
        history = self._conversation_store.get_history(conversation_id)
        results = self._retriever.retrieve(question, top_k=self._top_k)
        relevant = [r for r in results if r.score >= self._min_score]

        if not relevant:
            self._conversation_store.add_turn(conversation_id, question, NO_INFO_ANSWER)
            return ChatResponse(answer=NO_INFO_ANSWER, citations=[])

        messages = build_messages(question, relevant, history)
        answer = self._ollama_client.chat(
            self._chat_model, messages, num_predict=self._num_predict, keep_alive=self._keep_alive
        )

        citations = [
            Citation(
                document_id=r.document_id,
                page_start=r.page_start,
                page_end=r.page_end,
                chunk_id=r.chunk_id,
                score=r.score,
            )
            for r in relevant
        ]
        self._conversation_store.add_turn(conversation_id, question, answer)
        return ChatResponse(answer=answer, citations=citations)

    def ask_stream(self, conversation_id: str, question: str) -> Iterator[str | ChatResponse]:
        """Same retrieve-then-generate flow as `ask()`, but yields the answer as
        text fragments as they're generated, followed by a final `ChatResponse`
        carrying the full answer and citations. The "no information" fallback
        is yielded as a single fragment (nothing to stream token-by-token)."""
        history = self._conversation_store.get_history(conversation_id)
        results = self._retriever.retrieve(question, top_k=self._top_k)
        relevant = [r for r in results if r.score >= self._min_score]

        if not relevant:
            self._conversation_store.add_turn(conversation_id, question, NO_INFO_ANSWER)
            yield NO_INFO_ANSWER
            yield ChatResponse(answer=NO_INFO_ANSWER, citations=[])
            return

        messages = build_messages(question, relevant, history)
        fragments: list[str] = []
        for fragment in self._ollama_client.chat_stream(
            self._chat_model, messages, num_predict=self._num_predict, keep_alive=self._keep_alive
        ):
            fragments.append(fragment)
            yield fragment

        answer = "".join(fragments)
        citations = [
            Citation(
                document_id=r.document_id,
                page_start=r.page_start,
                page_end=r.page_end,
                chunk_id=r.chunk_id,
                score=r.score,
            )
            for r in relevant
        ]
        self._conversation_store.add_turn(conversation_id, question, answer)
        yield ChatResponse(answer=answer, citations=citations)
