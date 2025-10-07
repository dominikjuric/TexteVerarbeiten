#!/usr/bin/env python3
"""Formula search module."""

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from src.config import CFG


_ROOT = Path(__file__).resolve().parents[2]


def _resolve_db_path() -> Path:
    cfg = CFG.get("formulas", {})
    db_path = Path(cfg.get("index_db", "metadata/formula_index.sqlite")).expanduser()
    if not db_path.is_absolute():
        db_path = (_ROOT / db_path).resolve()
    return db_path


def search_by_symbol(symbol: str, limit: int = 10) -> list[dict]:
    """Search formulas containing a specific symbol/token."""
    db_path = _resolve_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        """
        SELECT f.hash, f.latex, f.doc_id, f.type, f.source
        FROM tokens t
        JOIN formulas f ON f.id = t.formula_id
        WHERE t.token = ?
        GROUP BY f.id
        LIMIT ?
        """,
        (symbol, limit),
    )

    rows = c.fetchall()

    conn.close()
    return [
        {
            "hash": row[0],
            "latex": row[1],
            "doc_id": row[2],
            "type": row[3],
            "source": row[4],
        }
        for row in rows
    ]


def search_by_pattern(pattern: str, limit: int = 10) -> list[dict]:
    """Search formulas matching a regex pattern."""
    db_path = _resolve_db_path()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    regex = re.compile(pattern)
    results = []

    c.execute("SELECT hash, latex, doc_id, type, source FROM formulas")

    for row in c.fetchall():
        h, latex, doc_id, formula_type, source = row
        if regex.search(latex):
            results.append({
                'hash': h,
                'latex': latex,
                'doc_id': doc_id,
                'type': formula_type,
                'source': source,
            })
            if len(results) >= limit:
                break
    
    conn.close()
    return results


def search_formulas(symbol: str = None, contains: str = None, limit: int = 10) -> list[dict]:
    """Search formulas by symbol and/or pattern."""
    db_path = _resolve_db_path()
    if not db_path.exists():
        print(f"Error: {db_path} not found. Run formula indexing first.")
        return []

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    hashes = set()

    # Search by symbol first
    if symbol:
        c.execute(
            """
            SELECT DISTINCT f.hash
            FROM tokens t
            JOIN formulas f ON f.id = t.formula_id
            WHERE t.token = ?
            """,
            (symbol,),
        )
        hashes.update(row[0] for row in c.fetchall())
    
    results = []
    
    if contains:
        # If we have symbol matches, filter them by pattern
        # Otherwise, search all formulas
        search_hashes = list(hashes) if hashes else None
        pattern = re.compile(contains)
        
        if search_hashes:
            # Filter existing hashes by pattern
            for h in search_hashes:
                c.execute(
                    "SELECT latex, doc_id, type, source FROM formulas WHERE hash = ?",
                    (h,),
                )
                row = c.fetchone()
                if row and pattern.search(row[0]):
                    results.append({
                        'hash': h,
                        'latex': row[0],
                        'doc_id': row[1],
                        'type': row[2],
                        'source': row[3],
                    })
        else:
            # Search all formulas by pattern
            c.execute("SELECT hash, latex, doc_id, type, source FROM formulas")
            for row in c.fetchall():
                h, latex, doc_id, formula_type, source = row
                if pattern.search(latex):
                    results.append({
                        'hash': h,
                        'latex': latex,
                        'doc_id': doc_id,
                        'type': formula_type,
                        'source': source,
                    })
                    if len(results) >= limit:
                        break
    else:
        # Just return symbol matches
        for h in list(hashes)[:limit]:
            c.execute(
                "SELECT latex, doc_id, type, source FROM formulas WHERE hash = ?",
                (h,),
            )
            row = c.fetchone()
            if row:
                results.append({
                    'hash': h,
                    'latex': row[0],
                    'doc_id': row[1],
                    'type': row[2],
                    'source': row[3],
                })
    
    conn.close()
    return results[:limit]


def _format_source(info: dict) -> str:
    source = info.get('source')
    if source:
        return f" :: {source}"
    return ""


def print_formula_results(results: Iterable[dict]):
    """Print formula search results in a formatted way."""
    print(f"{len(results)} Treffer")
    for result in results:
        latex_preview = result['latex'][:120]
        print(f"{result['hash']} :: {result['doc_id']}{_format_source(result)} :: {latex_preview}")
        if len(result['latex']) > 120:
            print("  [truncated]")
