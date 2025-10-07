#!/usr/bin/env python3
"""Utilities for extracting LaTeX formulas from Nougat markdown outputs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Match, Tuple

from tqdm import tqdm

from src.config import CFG
from src.pipeline.logging_utils import get_pipeline_logger, setup_pipeline_logging


FORMULA_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
FORMULA_INLINE = re.compile(r"(?<!\$)\$(.+?)\$(?!\$)")

_ROOT = Path(__file__).resolve().parents[2]
logger = get_pipeline_logger("formulas.extract")


@dataclass(frozen=True)
class ExtractionPaths:
    """Resolved directories/files used for formula processing."""

    markdown_dir: Path
    text_dir: Path
    metadata_file: Path


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (_ROOT / path).resolve()
    return path


def _get_paths() -> ExtractionPaths:
    cfg = CFG.get("formulas", {})
    markdown_dir = _resolve_path(cfg.get("markdown_dir", "processed/nougat_md"))
    text_dir = _resolve_path(cfg.get("text_dir", "processed/nougat_txt"))
    metadata_file = _resolve_path(cfg.get("metadata_file", "metadata/formulas.jsonl"))

    text_dir.mkdir(parents=True, exist_ok=True)
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    return ExtractionPaths(markdown_dir=markdown_dir, text_dir=text_dir, metadata_file=metadata_file)


def norm_formula(latex: str) -> str:
    """Normalize LaTeX formulas by stripping and collapsing whitespace."""

    return re.sub(r"\s+", " ", latex.strip())


def hash_formula(latex: str) -> str:
    """Return a short, deterministic hash for a LaTeX formula."""

    return hashlib.md5(latex.encode("utf-8")).hexdigest()[:12]


def extract_formulas_from_md(md_path: Path, *, deduplicate: bool = True) -> Tuple[str, List[dict]]:
    """Extract formulas from a Nougat markdown file.

    Args:
        md_path: Path to the markdown/mmd file.
        deduplicate: If ``True`` the same formula type/hash combination per document is only
            recorded once in the metadata while still replacing all occurrences in the text output.

    Returns:
        Tuple containing the processed text (with placeholders) and a list of metadata entries.
    """

    text = md_path.read_text(encoding="utf-8", errors="ignore")
    doc_id = md_path.stem
    formulas: List[dict] = []
    seen: set[Tuple[str, str, str]] = set()

    def register_formula(kind: str, raw_latex: str) -> str:
        latex = norm_formula(raw_latex)
        formula_hash = hash_formula(latex)
        key = (formula_hash, doc_id, kind)

        if not deduplicate or key not in seen:
            seen.add(key)
            formulas.append(
                {
                    "doc_id": doc_id,
                    "hash": formula_hash,
                    "type": kind,
                    "latex": latex,
                    "source": md_path.name,
                }
            )

        return f"FORMULA_{formula_hash}"

    def replace_block(match: Match[str]) -> str:
        placeholder = register_formula("block", match.group(1))
        return f"\n{placeholder}\n"

    def replace_inline(match: Match[str]) -> str:
        placeholder = register_formula("inline", match.group(1))
        return f" {placeholder} "

    replaced = FORMULA_BLOCK.sub(replace_block, text)
    replaced = FORMULA_INLINE.sub(replace_inline, replaced)

    return replaced, formulas


def _iter_markdown_files(path: Path) -> Iterator[Path]:
    yield from sorted(path.glob("*.md"))
    yield from sorted(path.glob("*.mmd"))


def process_all_markdown_files(*, show_progress: bool = True, deduplicate: bool = True) -> List[dict]:
    """Process all Nougat markdown files and return extracted formula records."""

    setup_pipeline_logging()
    paths = _get_paths()
    md_files = list(_iter_markdown_files(paths.markdown_dir))

    if not md_files:
        logger.warning("Keine Nougat-Markdowns unter %s gefunden.", paths.markdown_dir)
        return []

    logger.info("Starte Formel-Extraktion für %s Dateien", len(md_files))

    collected: List[dict] = []
    iterator = tqdm(md_files, desc="Formeln", unit="datei", disable=not show_progress, leave=False)

    for md_path in iterator:
        try:
            replaced, formulas = extract_formulas_from_md(md_path, deduplicate=deduplicate)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Formeln konnten aus %s nicht extrahiert werden", md_path.name)
            continue

        out_file = paths.text_dir / f"{md_path.stem}.txt"
        out_file.write_text(replaced, encoding="utf-8")
        collected.extend(formulas)

    return collected


def save_formulas_jsonl(formulas: Iterable[dict], output: Path) -> Path:
    """Persist extracted formulas as JSONL file."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in formulas:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output


def extract_all_formulas(*, show_progress: bool = True, deduplicate: bool = True) -> dict:
    """Extract formulas from all Nougat markdown files and persist metadata/text outputs."""

    setup_pipeline_logging()
    paths = _get_paths()
    md_files = list(_iter_markdown_files(paths.markdown_dir))

    summary = {
        "total": len(md_files),
        "processed": 0,
        "documents_with_formulas": 0,
        "documents_without_formulas": 0,
        "total_formulas": 0,
        "errors": [],
        "output_file": str(paths.metadata_file),
        "text_dir": str(paths.text_dir),
    }

    if not md_files:
        logger.warning("Keine Nougat-Markdowns unter %s gefunden.", paths.markdown_dir)
        return summary

    logger.info("Starte Formel-Extraktion für %s Dateien", len(md_files))

    iterator = tqdm(
        md_files,
        desc="Formel-Extraktion",
        unit="datei",
        disable=not show_progress,
        leave=False,
    )

    with paths.metadata_file.open("w", encoding="utf-8") as handle:
        for md_path in iterator:
            try:
                replaced, formulas = extract_formulas_from_md(md_path, deduplicate=deduplicate)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Formeln konnten aus %s nicht extrahiert werden", md_path.name)
                summary["errors"].append({"file": str(md_path), "error": str(exc)})
                continue

            try:
                out_file = paths.text_dir / f"{md_path.stem}.txt"
                out_file.write_text(replaced, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                logger.exception("Textersatz konnte nicht nach %s geschrieben werden", out_file)
                summary["errors"].append({"file": str(out_file), "error": str(exc)})
                continue

            for row in formulas:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

            summary["processed"] += 1
            summary["total_formulas"] += len(formulas)
            if formulas:
                summary["documents_with_formulas"] += 1
            else:
                summary["documents_without_formulas"] += 1

    logger.info(
        "Formel-Extraktion abgeschlossen – %s Dateien verarbeitet, %s Formeln erfasst",
        summary["processed"],
        summary["total_formulas"],
    )

    if summary["errors"]:
        logger.warning("Bei %s Dateien traten Fehler auf.", len(summary["errors"]))

    return summary


__all__ = [
    "ExtractionPaths",
    "extract_all_formulas",
    "extract_formulas_from_md",
    "hash_formula",
    "norm_formula",
    "process_all_markdown_files",
    "save_formulas_jsonl",
]
