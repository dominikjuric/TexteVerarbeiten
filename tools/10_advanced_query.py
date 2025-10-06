#!/usr/bin/env python3
import argparse, sqlite3
from whoosh import index
from whoosh.qparser import MultifieldParser
from pathlib import Path

INDEX_DIR = Path("processed/whoosh_index")  # wie vorher
FORMULA_DB = Path("metadata/formula_index.sqlite")

def get_docs_with_symbol(symbol):
    if not FORMULA_DB.exists():
        return set()
    conn = sqlite3.connect(FORMULA_DB)
    c = conn.cursor()
    rows = c.execute("""
        SELECT DISTINCT f.doc_id
        FROM tokens t JOIN formulas f ON f.hash = t.hash
        WHERE t.token = ?
    """,(symbol,)).fetchall()
    conn.close()
    return {r[0] for r in rows}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="Volltextfrage")
    ap.add_argument("--symbol", help="Formel-Symbol optional", required=False)
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()

    ix = index.open_dir(INDEX_DIR)
    with ix.searcher() as searcher:
        parser = MultifieldParser(["content"], schema=ix.schema)
        q = parser.parse(args.q)
        results = searcher.search(q, limit=50)
        hits = [(hit['filename'], hit.score) for hit in results]

    if args.symbol:
        symbol_docs = get_docs_with_symbol(args.symbol.replace("\\","\\\\"))  # escape
        hits = [h for h in hits if h[0].rsplit('.',1)[0] in symbol_docs]

    for i,(fname, score) in enumerate(hits[:args.k]):
        print(f"[{i+1}] {fname}  score={score:.2f}")

if __name__ == "__main__":
    main()