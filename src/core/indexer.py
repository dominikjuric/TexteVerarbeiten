"""Utilities for adding extracted documents to the vector store."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from src.config import CFG
from src.text.chunking import AdaptiveTextChunker

try:
    from sentence_transformers import SentenceTransformer

    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    SentenceTransformer = None  # type: ignore[assignment]

try:
    from src.vector_store import get_collection

    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False


RAG_CFG = CFG.get("rag", {})
PATHS_CFG = CFG.get("paths", {})
MODELS_CFG = CFG.get("models", {})

DEFAULT_COLLECTION = RAG_CFG.get("collection", "papers")
DEFAULT_PERSIST_PATH = RAG_CFG.get("persist_path") or PATHS_CFG.get("chroma", ".chroma")
DEFAULT_EMBEDDING_MODEL = MODELS_CFG.get("embedding", "all-MiniLM-L6-v2")

CHUNK_CFG = RAG_CFG.get("chunking", {})

_CHUNKER = AdaptiveTextChunker(
    base_chunk_size=int(CHUNK_CFG.get("size", 1200)),
    chunk_overlap=int(CHUNK_CFG.get("overlap", 200)),
    max_chunk_size=int(CHUNK_CFG.get("max_size", 2400)),
    large_document_threshold=int(CHUNK_CFG.get("large_document_threshold", 60_000)),
    target_chunk_count=int(CHUNK_CFG.get("target_chunk_count", 256)),
    min_chunk_size=int(CHUNK_CFG.get("min_size", 400)),
)

if EMBEDDING_AVAILABLE and VECTOR_STORE_AVAILABLE:
    try:
        _COLLECTION = get_collection(DEFAULT_COLLECTION, persist_path=DEFAULT_PERSIST_PATH)
    except Exception:  # noqa: BLE001
        EMBEDDING_AVAILABLE = False
        _COLLECTION = None
else:
    _COLLECTION = None


def purge_by_source(source: str) -> None:
    """Remove documents for ``source`` from the configured collection."""

    if not EMBEDDING_AVAILABLE or _COLLECTION is None:
        raise ImportError("Embedding dependencies not available")

    try:
        _COLLECTION.delete(where={"source": source})
    except Exception:  # noqa: BLE001
        pass


def chunk(text: str, max_chars: int = 1200) -> List[str]:
    """Split text into smaller segments using the adaptive chunker."""

    if max_chars != _CHUNKER.base_chunk_size:
        dynamic_chunker = AdaptiveTextChunker(
            base_chunk_size=max_chars,
            chunk_overlap=_CHUNKER.chunk_overlap,
            max_chunk_size=max(max_chars, _CHUNKER.max_chunk_size),
            large_document_threshold=_CHUNKER.large_document_threshold,
            target_chunk_count=_CHUNKER.target_chunk_count,
            min_chunk_size=_CHUNKER.min_chunk_size,
        )
        return [chunk.text for chunk in dynamic_chunker.chunk(text)]

    return [chunk.text for chunk in _CHUNKER.chunk(text)]


def add_document(doc_id: str, text: str, meta: Dict[str, object] | None) -> int:
    """Add document to the configured ChromaDB collection."""

    if not EMBEDDING_AVAILABLE or SentenceTransformer is None or _COLLECTION is None:
        raise ImportError(
            "Embedding dependencies not available. Install with: pip install sentence-transformers chromadb"
        )

    base_meta: Dict[str, object] = dict(meta or {})
    chunks = _CHUNKER.chunk(text)
    if not chunks:
        return 0

    embedder = _get_embedder(DEFAULT_EMBEDDING_MODEL)
    documents = [chunk.text for chunk in chunks]
    embeddings = embedder.encode(documents, convert_to_numpy=True).tolist()
    total = len(chunks)

    metadatas: List[Dict[str, object]] = []
    for chunk in chunks:
        chunk_meta: Dict[str, object] = dict(base_meta)
        chunk_meta.update(
            {
                "chunk_index": chunk.index,
                "chunk_count": total,
                "chunk_start": chunk.start,
                "chunk_end": chunk.end,
                "chunk_strategy": _CHUNKER.strategy_name,
            }
        )
        metadatas.append(chunk_meta)

    ids = [f"{doc_id}:{chunk.index}" for chunk in chunks]
    _COLLECTION.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    return total


@lru_cache(maxsize=4)
def _get_embedder(model_name: str) -> SentenceTransformer:
    if SentenceTransformer is None:
        raise ImportError("SentenceTransformer is not available")
    return SentenceTransformer(model_name)


__all__ = ["add_document", "purge_by_source", "chunk"]
