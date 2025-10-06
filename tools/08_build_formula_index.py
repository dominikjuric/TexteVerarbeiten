#!/usr/bin/env python3
import json, re, sqlite3
from pathlib import Path

FORMULAS = Path("metadata/formulas.jsonl")
DB = Path("metadata/formula_index.sqlite")

TOKEN_PATTERN = re.compile(r'[A-Za-z]+|\\[A-Za-z]+|[=+\-*/^_]')

def tokenize(latex: str):
    return TOKEN_PATTERN.findall(latex)

def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS formulas")
    c.execute("DROP TABLE IF EXISTS tokens")
    c.execute("CREATE TABLE formulas(hash TEXT PRIMARY KEY, doc_id TEXT, type TEXT, latex TEXT)")
    c.execute("CREATE TABLE tokens(token TEXT, hash TEXT)")
    # Indexe
    c.execute("CREATE INDEX idx_tokens_token ON tokens(token)")
    with FORMULAS.open() as f:
        for line in f:
            row = json.loads(line)
            c.execute("INSERT INTO formulas(hash, doc_id, type, latex) VALUES (?,?,?,?)",
                      (row["hash"], row["doc_id"], row["type"], row["latex"]))
            for tok in set(tokenize(row["latex"])):
                c.execute("INSERT INTO tokens(token, hash) VALUES (?,?)", (tok, row["hash"]))
    conn.commit()
    conn.close()
    print(f"Formel-Index erstellt: {DB}")

if __name__ == "__main__":
    main()