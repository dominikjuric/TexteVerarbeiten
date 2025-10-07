#!/usr/bin/env python3
"""Whoosh index building module."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

try:
    from whoosh import index
    from whoosh.analysis import StemmingAnalyzer
    from whoosh.fields import ID, TEXT, Schema

    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False
    index = None
    Schema = None
    ID = None
    TEXT = None
    StemmingAnalyzer = None

from .logging_utils import get_pipeline_logger, setup_pipeline_logging
from .utils import batched, ensure_directory


TXT_DIR = ensure_directory(Path("txt"))
INDEX_DIR = ensure_directory(Path("processed/whoosh_index"))

logger = get_pipeline_logger("index")

if WHOOSH_AVAILABLE:
    schema = Schema(
        doc_id=ID(stored=True, unique=True),
        filename=ID(stored=True),
        content=TEXT(stored=False, analyzer=StemmingAnalyzer()),
    )
else:
    schema = None


def build_whoosh_index(batch_size: Optional[int] = None, show_progress: bool = True) -> Dict[str, object]:
    """Build or update the Whoosh BM25 search index from text files."""

    setup_pipeline_logging()

    if not WHOOSH_AVAILABLE:
        message = "Whoosh nicht verfügbar. Installiere mit: pip install Whoosh"
        logger.error(message)
        return {"total": 0, "indexed": 0, "errors": [message]}

    if not index.exists_in(INDEX_DIR):
        ix = index.create_in(INDEX_DIR, schema)
        logger.info("Neuen Whoosh-Index unter %s angelegt", INDEX_DIR)
    else:
        ix = index.open_dir(INDEX_DIR)
        logger.info("Bestehenden Whoosh-Index unter %s aktualisieren", INDEX_DIR)

    writer = ix.writer()
    txt_files = sorted(TXT_DIR.glob("*.txt"))
    total = len(txt_files)
    summary: Dict[str, object] = {"total": total, "indexed": 0, "errors": []}

    if not txt_files:
        logger.warning("Keine Textdateien in %s gefunden", TXT_DIR)
        return summary

    batches: List[List[Path]]
    if batch_size and batch_size > 0 and batch_size < total:
        batches = list(batched(txt_files, batch_size))
    else:
        batches = [txt_files]

    for batch_index, batch in enumerate(batches, start=1):
        desc = f"Index-Batch {batch_index}/{len(batches)}"
        iterator = tqdm(batch, desc=desc, unit="datei", leave=False, disable=not show_progress)
        for txt in iterator:
            try:
                doc_id = txt.stem
                content = txt.read_text(encoding="utf-8", errors="ignore")
                writer.update_document(doc_id=doc_id, filename=txt.name, content=content)
                summary["indexed"] = int(summary["indexed"]) + 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Fehler beim Indexieren von %s", txt)
                summary["errors"].append({"file": str(txt), "error": str(exc)})

    writer.commit()

    logger.info(
        "Whoosh-Index erstellt/aktualisiert – %s Dokumente verarbeitet (%s Fehler)",
        summary["indexed"],
        len(summary["errors"]),
    )

    return summary
