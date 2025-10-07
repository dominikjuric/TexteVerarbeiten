#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path
from rapidfuzz import fuzz, process

RAW_DIRS_ENV = os.getenv("RAW_DIRS")
if RAW_DIRS_ENV:
    RAW_DIRS = [Path(p).expanduser() for p in RAW_DIRS_ENV.split(os.pathsep) if p.strip()]
else:
    RAW_DIRS = [Path("raw")]

THRESH = int(os.getenv("DUPLICATE_NAME_THRESHOLD", "90"))


def file_hash(path: Path, max_bytes: int = 200_000) -> str | None:
    """Return a stable hash for the beginning of a file (best effort)."""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            chunk = f.read(max_bytes)
            h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def iter_pdfs() -> list[Path]:
    pdfs: list[Path] = []
    for base in RAW_DIRS:
        if not base.exists():
            continue
        pdfs.extend(sorted(p for p in base.rglob("*.pdf") if p.is_file()))
    return pdfs


def main():
    files = iter_pdfs()
    if not files:
        print("Keine PDFs gefunden. Setze RAW_DIRS oder lege Dateien unter 'raw/' ab.")
        return
    names = [p.name for p in files]
    print(f"Gefundene PDFs: {len(files)}")

    hashes: dict[str | None, list[str]] = {}
    for p in files:
        h = file_hash(p)
        hashes.setdefault(h, []).append(p.name)

    dup_hash = {k: v for k, v in hashes.items() if k and len(v) > 1}
    if dup_hash:
        print("\n[Identische Inhalte (gleicher Hash)]")
        for h, group in dup_hash.items():
            print(f"- {h[:10]}: {group}")

    print("\n[Ähnliche Dateinamen (potentielle Duplikate / Tippfehler)]")
    reported: set[tuple[str, str]] = set()
    for name in names:
        matches = process.extract(name, names, scorer=fuzz.token_sort_ratio, limit=5)
        for cand, score, _ in matches:
            if cand == name or score < THRESH:
                continue
            pair = tuple(sorted([name, cand]))
            if pair in reported:
                continue
            reported.add(pair)
            print(f"{score:>3}% :: {pair[0]}  <>  {pair[1]}")
    print(f"\nHinweis: Prüfe Paare >= {THRESH}%. Entferne Tippfehler-Versionen oder vereinheitliche Schreibweise.")


if __name__ == "__main__":
    main()
