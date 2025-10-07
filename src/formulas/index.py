#!/usr/bin/env python3
"""Formula indexing module using SQLite."""

import json
import re
import sqlite3
from pathlib import Path

FORMULAS = Path("metadata/formulas.jsonl")
DB = Path("metadata/formula_index.sqlite")

TOKEN_PATTERN = re.compile(r'[A-Za-z]+|\\[A-Za-z]+|[=+\-*/^_]')


def tokenize_latex(latex: str) -> list[str]:
    """Extract tokens from LaTeX formula."""
    return TOKEN_PATTERN.findall(latex)


def create_formula_index() -> Path:
    """Create SQLite index for formulas."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    # Drop existing tables
    c.execute("DROP TABLE IF EXISTS formulas")
    c.execute("DROP TABLE IF EXISTS tokens")
    
    # Create tables
    c.execute("""
        CREATE TABLE formulas(
            hash TEXT PRIMARY KEY, 
            doc_id TEXT, 
            type TEXT, 
            latex TEXT
        )
    """)
    c.execute("""
        CREATE TABLE tokens(
            token TEXT, 
            hash TEXT
        )
    """)
    
    # Create indexes
    c.execute("CREATE INDEX idx_tokens_token ON tokens(token)")
    c.execute("CREATE INDEX idx_formulas_doc_id ON formulas(doc_id)")
    
    # Load formulas from JSONL
    if not FORMULAS.exists():
        print(f"Warning: {FORMULAS} not found. Run formula extraction first.")
        conn.close()
        return DB
    
    formula_count = 0
    token_count = 0
    
    with FORMULAS.open() as f:
        for line in f:
            row = json.loads(line)
            c.execute(
                "INSERT INTO formulas(hash, doc_id, type, latex) VALUES (?,?,?,?)",
                (row["hash"], row["doc_id"], row["type"], row["latex"])
            )
            formula_count += 1
            
            # Extract and index tokens
            tokens = set(tokenize_latex(row["latex"]))
            for tok in tokens:
                c.execute(
                    "INSERT INTO tokens(token, hash) VALUES (?,?)", 
                    (tok, row["hash"])
                )
                token_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"Formel-Index erstellt: {DB}")
    print(f"- {formula_count} Formeln indexiert")
    print(f"- {token_count} Token-Zuordnungen erstellt")
    
    return DB


def get_formula_stats() -> dict:
    """Get statistics about the formula index."""
    if not DB.exists():
        return {'error': 'Index not found'}
    
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM formulas")
    formula_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT token) FROM tokens")
    unique_tokens = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tokens")
    total_tokens = c.fetchone()[0]
    
    c.execute("SELECT type, COUNT(*) FROM formulas GROUP BY type")
    type_counts = dict(c.fetchall())
    
    conn.close()
    
    return {
        'total_formulas': formula_count,
        'unique_tokens': unique_tokens,
        'total_token_mappings': total_tokens,
        'formula_types': type_counts
    }