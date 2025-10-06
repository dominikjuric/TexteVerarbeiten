#!/usr/bin/env python3
from pathlib import Path
from whoosh import index
from whoosh.fields import Schema, ID, TEXT
from whoosh.analysis import StemmingAnalyzer

TXT_DIR = Path("txt")
INDEX_DIR = Path("processed/whoosh_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

schema = Schema(
    doc_id=ID(stored=True, unique=True),
    filename=ID(stored=True),
    content=TEXT(stored=False, analyzer=StemmingAnalyzer())
)

def main():
    if not index.exists_in(INDEX_DIR):
        ix = index.create_in(INDEX_DIR, schema)
    else:
        ix = index.open_dir(INDEX_DIR)
    writer = ix.writer()
    txt_files = list(TXT_DIR.glob("*.txt"))
    print(f"Indexiere {len(txt_files)} Textdateien...")
    for t in txt_files:
        doc_id = t.stem
        content = t.read_text(encoding="utf-8", errors="ignore")
        writer.update_document(doc_id=doc_id, filename=t.name, content=content)
    writer.commit()
    print("Index fertig.")

if __name__ == "__main__":
    main()