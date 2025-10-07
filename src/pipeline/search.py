#!/usr/bin/env python3
"""Whoosh search module."""

import argparse
from whoosh import index
from whoosh.qparser import MultifieldParser
from pathlib import Path

INDEX_DIR = Path("processed/whoosh_index")


def search_whoosh(query: str, k: int = 8):
    """Search the Whoosh index for documents matching the query."""
    ix = index.open_dir(INDEX_DIR)
    with ix.searcher() as searcher:
        parser = MultifieldParser(["content"], schema=ix.schema)
        q = parser.parse(query)
        results = searcher.search(q, limit=k)
        
        search_results = []
        for i, hit in enumerate(results):
            result = {
                'rank': i + 1,
                'filename': hit['filename'],
                'doc_id': hit['doc_id']
            }
            
            # Optional: kurze Vorschau (erste Seite aus txt)
            txt_path = Path("txt") / (hit['filename'].rsplit('.', 1)[0] + ".txt")
            if txt_path.exists():
                content = txt_path.read_text(encoding="utf-8", errors="ignore")
                if "[PAGE" in content:
                    first = content.split("[PAGE")[1][:300]
                    result['preview'] = first.replace("\n", " ")[:180] + "..."
                else:
                    result['preview'] = content[:180] + "..."
            
            search_results.append(result)
        
        return search_results


def print_search_results(results):
    """Print search results in a formatted way."""
    for result in results:
        print(f"[{result['rank']}] {result['filename']}")
        if 'preview' in result:
            print("  Vorschau:", result['preview'])
        print()