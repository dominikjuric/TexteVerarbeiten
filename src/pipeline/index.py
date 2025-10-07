#!/usr/bin/env python3
"""Whoosh index building module."""

from pathlib import Path
try:
    from whoosh import index
    from whoosh.fields import Schema, ID, TEXT
    from whoosh.analysis import StemmingAnalyzer
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False
    index = None
    Schema = None
    ID = None
    TEXT = None
    StemmingAnalyzer = None

TXT_DIR = Path("txt")
INDEX_DIR = Path("processed/whoosh_index")
INDEX_DIR.mkdir(parents=True, exist_ok=True)

if WHOOSH_AVAILABLE:
    schema = Schema(
        doc_id=ID(stored=True, unique=True),
        filename=ID(stored=True),
        content=TEXT(stored=False, analyzer=StemmingAnalyzer())
    )
else:
    schema = None


def build_whoosh_index():
    """
    Build or update the Whoosh BM25 search index from text files.
    
    Creates a new index or updates an existing one with all .txt files found
    in the configured text directory. Uses Whoosh's stemming analyzer for
    better search matching.
    
    Note:
        Requires Whoosh to be installed. Each document is indexed with:
        - doc_id: filename without extension (unique identifier)
        - filename: original .txt filename 
        - content: full text content (stemmed, not stored)
        
        Index is stored in processed/whoosh_index/ directory.
    """
    if not WHOOSH_AVAILABLE:
        print("Error: Whoosh not available. Install with: pip install Whoosh")
        return
    
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