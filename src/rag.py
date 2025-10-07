"""Simple Retrieval-Augmented Generation utilities without LangChain.

This module exposes a stateful :class:`SimpleRAGSession` that talks directly to
ChromaDB and the OpenAI chat completions API.  It keeps track of previous
questions/answers to provide conversational context, and it returns structured
source attributions for every response so that callers can surface citations in
their UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import chromadb
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from src.config import CFG


DEFAULT_MODEL = CFG.get("models", {}).get("chat", "gpt-4o-mini")
DEFAULT_EMBEDDING_MODEL = CFG.get("models", {}).get("embedding", "all-MiniLM-L6-v2")
DEFAULT_COLLECTION = CFG.get("rag", {}).get("collection", "papers")
DEFAULT_PERSIST_PATH = (
    CFG.get("rag", {}).get("persist_path")
    or CFG.get("paths", {}).get("chroma")
    or ".chroma"
)
DEFAULT_HISTORY_LIMIT = int(CFG.get("rag", {}).get("history_limit", 10))
DEFAULT_TEMPERATURE = float(CFG.get("rag", {}).get("temperature", 0.0))
DEFAULT_RESULTS_PER_QUERY = int(CFG.get("rag", {}).get("results_per_query", 5))



@dataclass
class SourceAttribution:
    """Represents a retrieved context chunk that informed an answer."""

    document: str
    metadata: Dict[str, Any]
    score: float
    chunk_id: str

    def display_label(self) -> str:
        """Human readable label for CLI output."""

        source = self.metadata.get("source") or self.metadata.get("path") or "Unbekannte Quelle"
        page = self.metadata.get("page")
        return f"{source} (Seite {page})" if page is not None else str(source)


@dataclass
class ConversationTurn:
    """Single question/answer exchange including retrieved sources."""

    question: str
    answer: str
    sources: List[SourceAttribution] = field(default_factory=list)


class SimpleRAGSession:
    """Stateful RAG helper that manages embeddings, retrieval and chat history."""

    def __init__(
        self,
        *,
        collection_name: str = "papers",
        persist_path: str = ".chroma",
        api_key: Optional[str] = None,
        chat_model: str = DEFAULT_MODEL,
        embedding_model: Optional[str] = None,
        temperature: float = 0.0,
        history_limit: int = 10,
    ) -> None:
        if api_key is None:
            api_key = CFG.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY fehlt. Bitte in der Umgebung setzen oder .env konfigurieren.")

        self._client = OpenAI(api_key=api_key)
        self._chat_model = chat_model
        self._temperature = temperature
        self._history_limit = history_limit

        if embedding_model is None:
            embedding_model = DEFAULT_EMBEDDING_MODEL

        self._embedder = SentenceTransformer(embedding_model)
        self._collection = (
            chromadb.PersistentClient(path=persist_path).get_or_create_collection(collection_name)
        )

        self._history: List[ConversationTurn] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def chat_model(self) -> str:
        """Return the currently configured chat model."""

        return self._chat_model

    def ask(self, question: str, *, k: Optional[int] = None) -> Dict[str, Any]:
        """Answer a question using retrieved context and conversation history.

        Returns a dictionary containing the generated answer, the retrieved
        sources and the updated conversation history for convenience.
        """

        if not question.strip():
            raise ValueError("Die Frage darf nicht leer sein.")

        if k is None:
            k = DEFAULT_RESULTS_PER_QUERY
        sources = self._retrieve_sources(question, k)
        context = self._build_context_prompt(sources)
        messages = self._build_messages(question, context)

        response = self._client.chat.completions.create(
            model=self._chat_model,
            temperature=self._temperature,
            messages=messages,
        )
        answer = response.choices[0].message.content.strip()
        answer_with_sources = self._append_source_section(answer, sources)

        turn = ConversationTurn(question=question, answer=answer_with_sources, sources=sources)
        self._append_history(turn)

        return {
            "answer": answer_with_sources,
            "sources": sources,
            "history": list(self._history),
        }

    def get_history(self) -> List[ConversationTurn]:
        """Return the stored conversation history."""

        return list(self._history)

    def clear_history(self) -> None:
        """Forget the conversation context."""

        self._history.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _retrieve_sources(self, question: str, k: int) -> List[SourceAttribution]:
        embedding = self._embedder.encode([question], convert_to_numpy=True)[0].tolist()

        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances", "ids"],
        )

        documents = self._flatten(results.get("documents"))
        metadatas = self._flatten(results.get("metadatas"))
        distances = self._flatten(results.get("distances"))
        ids = self._flatten(results.get("ids"))

        attributions: List[SourceAttribution] = []
        for doc, meta, distance, chunk_id in zip(documents, metadatas, distances, ids):
            if meta is None:
                meta = {}
            score = float(distance) if distance is not None else 0.0
            attributions.append(SourceAttribution(document=doc, metadata=meta, score=score, chunk_id=chunk_id))
        return attributions

    def _build_context_prompt(self, sources: Iterable[SourceAttribution]) -> str:
        sections = []
        for idx, source in enumerate(sources, start=1):
            header = f"[{idx}] {source.display_label()} — Abstand: {source.score:.4f}"
            sections.append(f"{header}\n{source.document.strip()}")
        return "\n\n".join(sections)

    def _build_messages(self, question: str, context: str) -> List[Dict[str, str]]:
        system_prompt = (
            "Du bist ein hilfreicher wissenschaftlicher Assistent. Beantworte Fragen "
            "ausschließlich anhand des bereitgestellten Kontexts. Wenn Informationen "
            "fehlen, gib dies offen an. Liefere am Ende deiner Antwort eine Liste "
            "der verwendeten Quellen im Format [Zahl]."
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # incorporate previous turns for conversational memory
        for turn in self._history[-self._history_limit :]:
            messages.append({"role": "user", "content": turn.question})
            messages.append({"role": "assistant", "content": turn.answer})

        user_prompt = (
            "Kontext:\n"
            f"{context if context else '---'}\n\n"
            f"Frage: {question}\n"
            "Formuliere eine fundierte Antwort in Deutsch."
        )
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _append_history(self, turn: ConversationTurn) -> None:
        self._history.append(turn)
        if len(self._history) > self._history_limit:
            overflow = len(self._history) - self._history_limit
            if overflow > 0:
                del self._history[0:overflow]

    @staticmethod
    def _flatten(nested: Optional[List[List[Any]]]) -> List[Any]:
        if not nested:
            return []
        return [item for group in nested for item in group]

    @staticmethod
    def _append_source_section(answer: str, sources: List[SourceAttribution]) -> str:
        if not sources:
            return f"{answer}\n\nQuellen: Keine passenden Treffer."

        lines = [f"[{idx}] {source.display_label()}" for idx, source in enumerate(sources, start=1)]
        joined = "\n".join(lines)
        return f"{answer}\n\nQuellen:\n{joined}"


__all__ = [
    "SimpleRAGSession",
    "SourceAttribution",
    "ConversationTurn",
    "DEFAULT_MODEL",
    "DEFAULT_EMBEDDING_MODEL",
]

