"""Public re-export for vector indexing helpers."""

from __future__ import annotations

from .core.indexer import add_document, chunk, purge_by_source

__all__ = ["add_document", "chunk", "purge_by_source"]
