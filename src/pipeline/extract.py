#!/usr/bin/env python3
"""Text extraction pipeline module."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from tqdm import tqdm

from ..core.convert_local import extract_pdf_metadata, extract_text_pymupdf
from ..config import CFG
from ..text.chunking import AdaptiveTextChunker
from .logging_utils import get_pipeline_logger, setup_pipeline_logging
from .utils import batched, ensure_directory


RAW_DIRS_ENV = os.getenv("RAW_DIRS")
if RAW_DIRS_ENV:
    RAW_DIRS = [Path(p).expanduser() for p in RAW_DIRS_ENV.split(os.pathsep) if p.strip()]
else:
    RAW_DIRS = [Path(CFG.get("paths", {}).get("raw", "raw"))]

PIPELINE_CFG = CFG.get("pipeline", {})
PATHS_CFG = CFG.get("paths", {})

OUT_DIR = ensure_directory(Path(os.getenv("TEXT_OUT_DIR", PATHS_CFG.get("text", "txt"))))
METADATA_DIR = ensure_directory(Path(os.getenv("METADATA_DIR", PATHS_CFG.get("metadata", "metadata"))))
CHUNK_DIR = ensure_directory(Path(os.getenv("CHUNK_DIR", PATHS_CFG.get("chunks", "processed/chunks"))))

CHUNK_CFG = CFG.get("rag", {}).get("chunking", {})

DEFAULT_PARALLELISM = int(
    os.getenv("PIPELINE_MAX_WORKERS")
    or PIPELINE_CFG.get("parallelism", 0)
    or 0
)

CHUNKER = AdaptiveTextChunker(
    base_chunk_size=int(os.getenv("CHUNK_SIZE", CHUNK_CFG.get("size", 1200))),
    chunk_overlap=int(os.getenv("CHUNK_OVERLAP", CHUNK_CFG.get("overlap", 200))),
    max_chunk_size=int(os.getenv("CHUNK_MAX_SIZE", CHUNK_CFG.get("max_size", 2400))),
    large_document_threshold=int(
        os.getenv("CHUNK_LARGE_THRESHOLD", CHUNK_CFG.get("large_document_threshold", 60_000))
    ),
    target_chunk_count=int(os.getenv("CHUNK_TARGET_COUNT", CHUNK_CFG.get("target_chunk_count", 256))),
    min_chunk_size=int(os.getenv("CHUNK_MIN_SIZE", CHUNK_CFG.get("min_size", 400))),
)

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


def _write_metadata(
    pdf_path: Path,
    text_path: Path,
    metadata: Dict[str, object],
    chunk_summary: Optional[Dict[str, object]],
) -> None:
    payload = {
        "pdf": str(pdf_path.resolve()),
        "text": str(text_path.resolve()),
        "extracted_at": datetime.now(tz=timezone.utc).isoformat(),
        "metadata": metadata,
        "chunks": chunk_summary,
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
    chunk_summary: Optional[Dict[str, object]] = None
    chunk_error: Optional[str] = None
    chunk_count = 0

    try:
        metadata_result = extract_pdf_metadata(str(pdf))
    except Exception as exc:  # noqa: BLE001
        metadata_error = str(exc)
        logger.exception("Metadaten konnten nicht gelesen werden für %s", pdf)

    if metadata_error:
        metadata_result = {"error": metadata_error, "fallback_title": pdf.stem}

    try:
        chunks = CHUNKER.chunk(content)
        chunk_count = len(chunks)
        chunk_path = CHUNK_DIR / f"{pdf.stem}.chunks.jsonl"
        lengths = [chunk.length for chunk in chunks]

        with chunk_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                record = {
                    "index": chunk.index,
                    "text": chunk.text,
                    "char_start": chunk.start,
                    "char_end": chunk.end,
                    "strategy": CHUNKER.strategy_name,
                }
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")

        chunk_summary = {
            "count": chunk_count,
            "path": str(chunk_path.resolve()),
            "strategy": CHUNKER.strategy_name,
        }
        if lengths:
            chunk_summary["avg_chars"] = int(sum(lengths) / len(lengths))
            chunk_summary["max_chars"] = max(lengths)
    except Exception as exc:  # noqa: BLE001
        chunk_error = str(exc)
        chunk_summary = {
            "strategy": CHUNKER.strategy_name,
            "error": chunk_error,
        }
        logger.exception("Chunking fehlgeschlagen für %s", pdf)

    _write_metadata(pdf, text_path, metadata_result, chunk_summary)

    logger.info("✅ %s verarbeitet", pdf.name)
    return {
        "status": "processed",
        "metadata_error": metadata_error,
        "chunks": chunk_count,
        "chunk_error": chunk_error,
    }


def extract_all_pdfs(
    batch_size: Optional[int] = None,
    overwrite: bool = False,
    show_progress: bool = True,
    parallelism: Optional[int] = None,
) -> Dict[str, object]:
    """Process all PDFs from ``RAW_DIRS`` and persist text + metadata."""

    setup_pipeline_logging()

    effective_parallelism = _effective_parallelism(parallelism)

    pdfs = list(iter_pdfs())
    total = len(pdfs)
    summary: Dict[str, object] = {
        "total": total,
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "metadata_errors": 0,
        "chunks": 0,
        "chunk_errors": [],
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

    def handle_result(pdf: Path, result: Dict[str, object]) -> None:
        status = result.get("status")
        if status == "processed":
            summary["processed"] = int(summary["processed"]) + 1
            summary["chunks"] = int(summary["chunks"]) + int(result.get("chunks", 0))
            if result.get("metadata_error"):
                summary["metadata_errors"] = int(summary["metadata_errors"]) + 1
            if result.get("chunk_error"):
                summary["chunk_errors"].append({"pdf": str(pdf), "error": result["chunk_error"]})
                logger.warning(
                    "Chunking konnte für %s nicht abgeschlossen werden: %s",
                    pdf.name,
                    result["chunk_error"],
                )
        elif status == "skipped":
            summary["skipped"] = int(summary["skipped"]) + 1
        elif status == "error":
            summary["errors"].append({"pdf": str(pdf), "error": result.get("error")})
            logger.error("❌ Fehler bei %s: %s", pdf.name, result.get("error"))

    for batch_index, batch in enumerate(batches, start=1):
        desc = f"Batch {batch_index}/{len(batches)}"
        if effective_parallelism:
            progress = (
                tqdm(total=len(batch), desc=desc, unit="pdf", leave=False, disable=not show_progress)
                if show_progress
                else None
            )
            with ThreadPoolExecutor(max_workers=effective_parallelism) as executor:
                futures = {executor.submit(_process_single_pdf, pdf, overwrite): pdf for pdf in batch}
                for future in as_completed(futures):
                    pdf = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Unerwarteter Fehler bei %s", pdf)
                        result = {"status": "error", "error": str(exc)}
                    handle_result(pdf, result)
                    if progress:
                        progress.update(1)
            if progress:
                progress.close()
        else:
            iterator = tqdm(batch, desc=desc, unit="pdf", leave=False, disable=not show_progress)
            for pdf in iterator:
                result = _process_single_pdf(pdf, overwrite=overwrite)
                handle_result(pdf, result)

    logger.info(
        "Verarbeitung abgeschlossen – %s verarbeitet, %s übersprungen, %s Fehler",
        summary["processed"],
        summary["skipped"],
        len(summary["errors"]),
    )
    if summary["metadata_errors"]:
        logger.warning("Metadaten konnten für %s Dateien nicht gelesen werden", summary["metadata_errors"])
    if summary["chunks"]:
        logger.info(
            "Chunking-Strategie %s lieferte insgesamt %s Textsegmente",
            CHUNKER.strategy_name,
            summary["chunks"],
        )
    if summary["chunk_errors"]:
        logger.warning("Chunking scheiterte bei %s Dateien", len(summary["chunk_errors"]))

    return summary


def _effective_parallelism(parallelism: Optional[int]) -> Optional[int]:
    if parallelism is None:
        parallelism = DEFAULT_PARALLELISM
    if not parallelism or parallelism <= 1:
        return None
    cpu_count = os.cpu_count() or parallelism
    allowed = min(parallelism, cpu_count)
    return allowed if allowed > 1 else None
