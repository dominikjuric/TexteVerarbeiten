#!/usr/bin/env python3
import argparse, os, sys, hashlib
from pathlib import Path
from src.dispatcher import process_pdf

def make_doc_id(p: Path) -> str:
    # stabil & kollisionsarm: <stem>_<hash8>
    h = hashlib.sha1(str(p.resolve()).encode()).hexdigest()[:8]
    return f"{p.stem}_{h}"

def iter_pdfs(paths):
    for inp in paths:
        p = Path(inp)
        if p.is_dir():
            for q in sorted(p.rglob("*.pdf")):
                if q.is_file():
                    yield q
        elif p.is_file() and p.suffix.lower() == ".pdf":
            yield p
        else:
            print(f"[skip] {p} ist kein PDF/Ordner", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description="Process one or more PDFs into the local vector index")
    ap.add_argument("paths", nargs="+", help="PDF-Datei(en) oder Ordner")
    ap.add_argument("--tag", default="", help="optional: Tag/Notiz in die Metadaten")
    args = ap.parse_args()

    any_ok = False
    for pdf in iter_pdfs(args.paths):
        doc_id = make_doc_id(pdf)
        meta = {
            "source": str(pdf),
            "filename": pdf.name,
            "tag": args.tag
        }
        try:
            res = process_pdf(doc_id, str(pdf), meta)
            print(f"[ok] {pdf} -> {res}")
            any_ok = True
        except Exception as e:
            print(f"[err] {pdf}: {e}", file=sys.stderr)

    if not any_ok:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
