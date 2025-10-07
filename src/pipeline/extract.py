#!/usr/bin/env python3
"""Text extraction pipeline module."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from tqdm import tqdm

from ..core.convert_local import extract_pdf_metadata, extract_text_pymupdf
from .logging_utils import get_pipeline_logger, setup_pipeline_logging
from .utils import batched, ensure_directory


RAW_DIRS_ENV = os.getenv("RAW_DIRS")
if RAW_DIRS_ENV:
    RAW_DIRS = [Path(p).expanduser() for p in RAW_DIRS_ENV.split(os.pathsep) if p.strip()]
else:
    RAW_DIRS = [Path("raw")]

OUT_DIR = ensure_directory(Path(os.getenv("TEXT_OUT_DIR", "txt")))
METADATA_DIR = ensure_directory(Path(os.getenv("METADATA_DIR", "metadata")))

logger = get_pipeline_logger("extract")


def iter_pdfs() -> Iterator[Path]:
    """Iterate over all PDF files in the raw directories."""

    for base in RAW_DIRS:
        if not base.exists():
            logger.debug("Überspringe fehlendes Eingabeverzeichnis %s", base)
            continue
        for pdf in sorted(base.rglob("*.pdf")):
            if pdf.is_file():
                yield pdf


def extract_pdf(pdf_path: Path) -> str:
    """Return text extracted with PyMuPDF."""

    text = extract_text_pymupdf(str(pdf_path))
    return text if text.strip() else ""


def _metadata_path(pdf_path: Path) -> Path:
    return METADATA_DIR / f"{pdf_path.stem}.json"


def _write_metadata(pdf_path: Path, text_path: Path, metadata: Dict[str, object]) -> None:
    payload = {
        "pdf": str(pdf_path.resolve()),
        "text": str(text_path.resolve()),
        "extracted_at": datetime.now(tz=timezone.utc).isoformat(),
        "metadata": metadata,
    }
    _metadata_path(pdf_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _process_single_pdf(pdf: Path, overwrite: bool) -> Dict[str, object]:
    text_path = OUT_DIR / (pdf.stem + ".txt")

    if text_path.exists() and not overwrite:
        logger.info("Überspringe %s – Ausgabe existiert bereits", pdf.name)
        return {"status": "skipped", "reason": "exists"}

    try:
        content = extract_pdf(pdf)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Textextraktion fehlgeschlagen für %s", pdf)
        return {"status": "error", "error": str(exc)}

    if not content:
        logger.warning("Keine extrahierbaren Inhalte in %s gefunden", pdf)
        return {"status": "skipped", "reason": "empty"}

    text_path.write_text(content, encoding="utf-8")
    metadata_result: Dict[str, object] = {}
    metadata_error: Optional[str] = None

    try:
        metadata_result = extract_pdf_metadata(str(pdf))
    except Exception as exc:  # noqa: BLE001
        metadata_error = str(exc)
        logger.exception("Metadaten konnten nicht gelesen werden für %s", pdf)

    if metadata_error:
        metadata_result = {"error": metadata_error, "fallback_title": pdf.stem}

    _write_metadata(pdf, text_path, metadata_result)

    logger.info("✅ %s verarbeitet", pdf.name)
    return {
        "status": "processed",
        "metadata_error": metadata_error,
    }


def extract_all_pdfs(
    batch_size: Optional[int] = None,
    overwrite: bool = False,
    show_progress: bool = True,
) -> Dict[str, object]:
    """Process all PDFs from ``RAW_DIRS`` and persist text + metadata."""

    setup_pipeline_logging()

    pdfs = list(iter_pdfs())
    total = len(pdfs)
    summary: Dict[str, object] = {
        "total": total,
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "metadata_errors": 0,
    }

    if not pdfs:
        logger.warning("Keine PDFs gefunden. Passe RAW_DIRS an oder lege Dateien unter 'raw/' ab.")
        return summary

    logger.info("Starte Batch-Verarbeitung für %s PDFs", total)

    batches: List[List[Path]]
    if batch_size and batch_size > 0 and batch_size < total:
        batches = list(batched(pdfs, batch_size))
    else:
        batches = [pdfs]

    for batch_index, batch in enumerate(batches, start=1):
        desc = f"Batch {batch_index}/{len(batches)}"
        iterator = tqdm(batch, desc=desc, unit="pdf", leave=False, disable=not show_progress)
        for pdf in iterator:
            result = _process_single_pdf(pdf, overwrite=overwrite)
            status = result["status"]
            if status == "processed":
                summary["processed"] = int(summary["processed"]) + 1
                if result.get("metadata_error"):
                    summary["metadata_errors"] = int(summary["metadata_errors"]) + 1
            elif status == "skipped":
                summary["skipped"] = int(summary["skipped"]) + 1
            elif status == "error":
                summary["errors"].append({"pdf": str(pdf), "error": result.get("error")})
                logger.error("❌ Fehler bei %s: %s", pdf.name, result.get("error"))

    logger.info(
        "Verarbeitung abgeschlossen – %s verarbeitet, %s übersprungen, %s Fehler",
        summary["processed"],
        summary["skipped"],
        len(summary["errors"]),
    )
    if summary["metadata_errors"]:
        logger.warning("Metadaten konnten für %s Dateien nicht gelesen werden", summary["metadata_errors"])

    return summary
