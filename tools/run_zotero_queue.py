#!/usr/bin/env python3
import os, sys, hashlib
from pathlib import Path
import argparse
from pyzotero import zotero
from src.config import CFG
from src.dispatcher import process_pdf
from src.indexer import purge_by_source

def get_zot():
    api_key = CFG.get("ZOTERO_API_KEY")
    user_id = CFG.get("ZOTERO_USER_ID")
    lib_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")
    group_id = os.getenv("ZOTERO_GROUP_ID")
    if lib_type == "group":
        if not group_id:
            raise RuntimeError("ZOTERO_LIBRARY_TYPE='group', aber ZOTERO_GROUP_ID fehlt.")
        return zotero.Zotero(group_id, "group", api_key)
    if not user_id or not api_key:
        raise RuntimeError("ZOTERO_USER_ID oder ZOTERO_API_KEY fehlt (siehe .env).")
    return zotero.Zotero(user_id, "user", api_key)

def make_doc_id(p: Path) -> str:
    h = hashlib.sha1(str(p.resolve()).encode()).hexdigest()[:8]
    return f"{p.stem}_{h}"

def resolve_pdf_path(att: dict, storage_dir: Path) -> Path | None:
    d = att.get("data", {})
    # 1) verlinkte Datei?
    link_path = d.get("path")
    if link_path:
        p = Path(link_path).expanduser()
        return p if p.exists() else None
    # 2) importierte Datei im Zotero-Storage
    key = d.get("key")
    filename = d.get("filename")
    if key and filename:
        p = storage_dir / key / filename
        return p if p.exists() else None
    return None

def set_tags(zot: zotero.Zotero, item: dict, remove: set[str], add: set[str], dry_run=False):
    tags = {t["tag"] for t in item["data"].get("tags", [])}
    tags -= remove
    tags |= add
    new_tags = [{"tag": t} for t in sorted(tags)]
    if dry_run:
        return
    item["data"]["tags"] = new_tags
    zot.update_item(item)

def main():
    ap = argparse.ArgumentParser(description="Abarbeiten der Zotero-Queue: /to_process -> verarbeiten -> /processed")
    ap.add_argument("--max", type=int, default=5, help="maximale Anzahl Items")
    ap.add_argument("--tag", default="/to_process", help="Eingangstag")
    ap.add_argument("--done", default="/processed", help="Zieltag nach Erfolg")
    ap.add_argument("--fail", default="/error", help="Fehltag bei Fehler")
    ap.add_argument("--storage-dir", default=os.getenv("ZOTERO_STORAGE_DIR", "~/Zotero/storage"),
                    help="Zotero storage directory (für importierte Anhänge)")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
    args = ap.parse_args()

    storage_dir = Path(args.storage_dir).expanduser()
    zot = get_zot()
    items = zot.items(tag=args.tag, limit=args.max, sort="dateAdded", direction="asc")

    if not items:
        print(f"Keine Items mit Tag '{args.tag}' gefunden.")
        return 0

    for it in items:
        title = it["data"].get("title") or it["key"]
        key = it["key"]
        children = zot.children(key)
        pdfs = [c for c in children if c["data"].get("itemType") == "attachment" and (
                (c["data"].get("contentType") or "").lower().startswith("application/pdf")
                or (c["data"].get("filename") or "").lower().endswith(".pdf")
                or c["data"].get("path", "").lower().endswith(".pdf")
        )]
        if not pdfs:
            print(f"[skip] {title} ({key}) – kein PDF-Anhang")
            set_tags(zot, it, remove=set(), add={args.fail}, dry_run=args.dry_run)
            continue

        # nimm den ersten PDF-Anhang, alternativ könntest du hier bestes/neueste wählen
        att = pdfs[0]
        pdf_path = resolve_pdf_path(att, storage_dir)
        if not pdf_path:
            print(f"[skip] {title} ({key}) – PDF-Datei nicht gefunden (Storage: {storage_dir})")
            set_tags(zot, it, remove=set(), add={args.fail}, dry_run=args.dry_run)
            continue

        meta = {
            "source": str(pdf_path),
            "filename": pdf_path.name,
            "zotero_key": key,
            "title": title
        }
        doc_id = make_doc_id(pdf_path)

        try:
            # Duplikate entfernen, dann indexieren
            purge_by_source(meta["source"])
            res = process_pdf(doc_id, str(pdf_path), meta)
            print(f"[ok] {title} -> {res}")
            set_tags(zot, it, remove={args.tag, args.fail}, add={args.done}, dry_run=args.dry_run)
        except Exception as e:
            print(f"[err] {title}: {e}")
            set_tags(zot, it, remove={args.tag}, add={args.fail}, dry_run=args.dry_run)

    return 0

if __name__ == "__main__":
    sys.exit(main())
