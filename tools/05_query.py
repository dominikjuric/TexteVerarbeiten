#!/usr/bin/env python3
import argparse
from whoosh import index
from whoosh.qparser import MultifieldParser
from pathlib import Path

INDEX_DIR = Path("processed/whoosh_index")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", required=True, help="Suchanfrage")
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    ix = index.open_dir(INDEX_DIR)
    with ix.searcher() as searcher:
        parser = MultifieldParser(["content"], schema=ix.schema)
        q = parser.parse(args.q)
        results = searcher.search(q, limit=args.k)
        for i, hit in enumerate(results):
            print(f"[{i+1}] {hit['filename']}")
            # Optional: kurze Vorschau (erste Seite aus txt)
            txt_path = Path("txt") / (hit['filename'].rsplit('.',1)[0] + ".txt")
            if txt_path.exists():
                first = txt_path.read_text(encoding="utf-8", errors="ignore").split("[PAGE")[1][:300]
                print("  Vorschau:", first.replace("\n"," ")[:180], "...")
            print()

if __name__ == "__main__":
    main()