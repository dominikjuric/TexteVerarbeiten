#!/usr/bin/env python3
"""Create and query a SQLite index for extracted LaTeX formulas."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterator

from src.config import CFG
from src.pipeline.logging_utils import get_pipeline_logger, setup_pipeline_logging


TOKEN_PATTERN = re.compile(r"[A-Za-z]+|\\[A-Za-z]+|[=+\-*/^_{}]")

_ROOT = Path(__file__).resolve().parents[2]
logger = get_pipeline_logger("formulas.index")


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = (_ROOT / path).resolve()
    return path


def _get_paths() -> tuple[Path, Path]:
    cfg = CFG.get("formulas", {})
    metadata_file = _resolve_path(cfg.get("metadata_file", "metadata/formulas.jsonl"))
    db_path = _resolve_path(cfg.get("index_db", "metadata/formula_index.sqlite"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return metadata_file, db_path


def tokenize_latex(latex: str) -> list[str]:
    """Split LaTeX expressions into searchable tokens."""

    return TOKEN_PATTERN.findall(latex)


def _iter_formula_rows(metadata_file: Path) -> Iterator[Dict[str, object]]:
    with metadata_file.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Zeile %s in %s konnte nicht geparst werden: %s", line_no, metadata_file, exc)


def _initialise_schema(cursor: sqlite3.Cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS tokens")
    cursor.execute("DROP TABLE IF EXISTS formulas")
    cursor.execute(
        """
        CREATE TABLE formulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            type TEXT NOT NULL,
            latex TEXT NOT NULL,
            source TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE tokens (
            token TEXT NOT NULL,
            formula_id INTEGER NOT NULL,
            FOREIGN KEY(formula_id) REFERENCES formulas(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute("CREATE INDEX idx_formulas_hash ON formulas(hash)")
    cursor.execute("CREATE INDEX idx_formulas_doc_id ON formulas(doc_id)")
    cursor.execute("CREATE INDEX idx_tokens_token ON tokens(token)")


def create_formula_index() -> dict:
    """Create the SQLite index for formula search and return a summary."""

    setup_pipeline_logging()
    metadata_file, db_path = _get_paths()

    summary = {
        "total": 0,
        "indexed": 0,
        "token_mappings": 0,
        "db_path": str(db_path),
        "errors": [],
    }

    if not metadata_file.exists():
        warning = f"Formel-Metadatendatei fehlt: {metadata_file}"
        logger.warning(warning)
        summary["errors"].append({"file": str(metadata_file), "error": "not found"})
        return summary

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    _initialise_schema(cursor)

    try:
        for row in _iter_formula_rows(metadata_file):
            summary["total"] += 1
            try:
                cursor.execute(
                    "INSERT INTO formulas(hash, doc_id, type, latex, source) VALUES (?,?,?,?,?)",
                    (
                        str(row.get("hash", "")),
                        str(row.get("doc_id", "")),
                        str(row.get("type", "")),
                        str(row.get("latex", "")),
                        row.get("source"),
                    ),
                )
                formula_id = cursor.lastrowid
            except sqlite3.Error as exc:
                logger.exception("Formel konnte nicht eingefügt werden: %s", row)
                summary["errors"].append({"hash": row.get("hash"), "error": str(exc)})
                continue

            tokens = set(tokenize_latex(str(row.get("latex", ""))))
            if tokens:
                cursor.executemany(
                    "INSERT INTO tokens(token, formula_id) VALUES (?, ?)",
                    ((token, formula_id) for token in tokens),
                )
                summary["token_mappings"] += len(tokens)

            summary["indexed"] += 1

        connection.commit()
    finally:
        connection.close()

    logger.info(
        "Formel-Index erstellt unter %s – %s Formeln, %s Token",
        db_path,
        summary["indexed"],
        summary["token_mappings"],
    )

    if summary["errors"]:
        logger.warning("Beim Indexaufbau traten %s Fehler auf.", len(summary["errors"]))

    return summary


def get_formula_stats() -> dict:
    """Return aggregate statistics about the formula index."""

    _, db_path = _get_paths()

    if not db_path.exists():
        return {"error": "index not found", "db_path": str(db_path)}

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM formulas")
        total_formulas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM formulas")
        distinct_docs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT token) FROM tokens")
        unique_tokens = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tokens")
        total_mappings = cursor.fetchone()[0]
    finally:
        connection.close()

    return {
        "total_formulas": total_formulas,
        "documents": distinct_docs,
        "unique_tokens": unique_tokens,
        "total_token_mappings": total_mappings,
        "db_path": str(db_path),
    }


__all__ = ["create_formula_index", "get_formula_stats", "tokenize_latex"]
