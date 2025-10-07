#!/usr/bin/env python3
"""Formula search module."""

import sqlite3
import argparse
import re
from pathlib import Path

DB = Path("metadata/formula_index.sqlite")


def search_by_symbol(symbol: str, limit: int = 10) -> list[dict]:
    """Search formulas containing a specific symbol/token."""
    if not DB.exists():
        return []
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Get all hashes containing the symbol
    c.execute("SELECT hash FROM tokens WHERE token = ?", (symbol,))
    hashes = [row[0] for row in c.fetchall()]
    
    results = []
    for h in hashes[:limit]:
        c.execute("SELECT latex, doc_id, type FROM formulas WHERE hash = ?", (h,))
        row = c.fetchone()
        if row:
            results.append({
                'hash': h,
                'latex': row[0],
                'doc_id': row[1],
                'type': row[2]
            })
    
    conn.close()
    return results


def search_by_pattern(pattern: str, limit: int = 10) -> list[dict]:
    """Search formulas matching a regex pattern."""
    if not DB.exists():
        return []
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Get all formulas
    c.execute("SELECT hash, latex, doc_id, type FROM formulas")
    
    regex = re.compile(pattern)
    results = []
    
    for row in c.fetchall():
        h, latex, doc_id, formula_type = row
        if regex.search(latex):
            results.append({
                'hash': h,
                'latex': latex,
                'doc_id': doc_id,
                'type': formula_type
            })
            if len(results) >= limit:
                break
    
    conn.close()
    return results


def search_formulas(symbol: str = None, contains: str = None, limit: int = 10) -> list[dict]:
    """Search formulas by symbol and/or pattern."""
    if not DB.exists():
        print(f"Error: {DB} not found. Run formula indexing first.")
        return []
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hashes = set()
    
    # Search by symbol first
    if symbol:
        c.execute("SELECT hash FROM tokens WHERE token = ?", (symbol,))
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
                c.execute("SELECT latex, doc_id, type FROM formulas WHERE hash = ?", (h,))
                row = c.fetchone()
                if row and pattern.search(row[0]):
                    results.append({
                        'hash': h,
                        'latex': row[0],
                        'doc_id': row[1],
                        'type': row[2]
                    })
        else:
            # Search all formulas by pattern
            c.execute("SELECT hash, latex, doc_id, type FROM formulas")
            for row in c.fetchall():
                h, latex, doc_id, formula_type = row
                if pattern.search(latex):
                    results.append({
                        'hash': h,
                        'latex': latex,
                        'doc_id': doc_id,
                        'type': formula_type
                    })
                    if len(results) >= limit:
                        break
    else:
        # Just return symbol matches
        for h in list(hashes)[:limit]:
            c.execute("SELECT latex, doc_id, type FROM formulas WHERE hash = ?", (h,))
            row = c.fetchone()
            if row:
                results.append({
                    'hash': h,
                    'latex': row[0],
                    'doc_id': row[1],
                    'type': row[2]
                })
    
    conn.close()
    return results[:limit]


def print_formula_results(results: list[dict]):
    """Print formula search results in a formatted way."""
    print(f"{len(results)} Treffer")
    for result in results:
        latex_preview = result['latex'][:120]
        print(f"{result['hash']} :: {result['doc_id']} :: {latex_preview}")
        if len(result['latex']) > 120:
            print("  [truncated]")