"""Shared helpers for working with the Chroma vector database."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.config import CFG

try:
    import chromadb
    from chromadb.config import Settings

    CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None  # type: ignore[assignment]
    Settings = None  # type: ignore[assignment]
    CHROMA_AVAILABLE = False

if TYPE_CHECKING:
    from chromadb.api.models import Collection


def _settings_for(path: str, overrides: Optional[Dict[str, Any]] = None) -> Settings:
    if not CHROMA_AVAILABLE or Settings is None:
        raise ImportError("ChromaDB ist nicht installiert. Bitte chromadb nachinstallieren.")

    overrides = overrides or {}
    defaults = {
        "chroma_db_impl": overrides.get("chroma_db_impl", "duckdb+parquet"),
        "persist_directory": path,
        "anonymized_telemetry": overrides.get("anonymized_telemetry", False),
        "allow_reset": overrides.get("allow_reset", False),
        "is_persistent": True,
    }
    return Settings(**defaults)


@lru_cache(maxsize=4)
def get_client(path: Optional[str] = None) -> chromadb.PersistentClient:
    if not CHROMA_AVAILABLE or chromadb is None:
        raise ImportError("ChromaDB ist nicht installiert. Bitte chromadb nachinstallieren.")

    rag_cfg = CFG.get("rag", {})
    overrides = rag_cfg.get("chroma_settings", {})
    resolved_path = path or rag_cfg.get("persist_path") or CFG.get("paths", {}).get("chroma", ".chroma")
    settings = _settings_for(resolved_path, overrides)
    return chromadb.PersistentClient(settings=settings)


@lru_cache(maxsize=16)
def get_collection(
    name: str,
    *,
    persist_path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> "Collection":
    client = get_client(persist_path)
    rag_cfg = CFG.get("rag", {})
    metadata_overrides = rag_cfg.get("collection_metadata", {})
    combined_metadata: Dict[str, Any] = {"hnsw:space": "cosine"}
    combined_metadata.update(metadata_overrides)
    if metadata:
        combined_metadata.update(metadata)
    return client.get_or_create_collection(name, metadata=combined_metadata)


__all__ = ["get_client", "get_collection"]
