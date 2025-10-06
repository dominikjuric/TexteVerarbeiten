#!/usr/bin/env python3
import sqlite3, argparse, re
from pathlib import Path

DB = Path("metadata/formula_index.sqlite")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", help="Symbol / Token (z.B. Re, u, v, sum)", required=False)
    ap.add_argument("--contains", help="Regex über Latex (z.B. velocity|omega)", required=False)
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    hashes = set()

    if args.symbol:
        for row in c.execute("SELECT hash FROM tokens WHERE token = ?", (args.symbol,)):
            hashes.add(row[0])

    results = []
    if args.contains:
        pattern = re.compile(args.contains)
        for h in list(hashes) if hashes else [r[0] for r in c.execute("SELECT hash FROM formulas")]:
            (latex, doc_id) = c.execute("SELECT latex, doc_id FROM formulas WHERE hash=?", (h,)).fetchone()
            if pattern.search(latex):
                results.append((h, doc_id, latex))
    else:
        for h in hashes:
            (latex, doc_id) = c.execute("SELECT latex, doc_id FROM formulas WHERE hash=?", (h,)).fetchone()
            results.append((h, doc_id, latex))

    print(f"{len(results)} Treffer")
    for (h, doc_id, latex) in results[:args.limit]:
        print(f"{h} :: {doc_id} :: {latex[:120]}")

if __name__ == "__main__":
    main()