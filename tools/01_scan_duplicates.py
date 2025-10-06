#!/usr/bin/env python3
import hashlib
from pathlib import Path
from rapidfuzz import fuzz, process

RAW_DIR = Path("raw/Paper")
THRESH = 90  # Nameähnlichkeit (0–100)

def file_hash(path: Path, max_bytes=200_000):
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            chunk = f.read(max_bytes)
            h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def main():
    files = [p for p in RAW_DIR.glob("*.pdf")]
    names = [p.name for p in files]
    print(f"Gefundene PDFs: {len(files)}")
    # Hashes
    hashes = {}
    for p in files:
        h = file_hash(p)
        hashes.setdefault(h, []).append(p.name)

    dup_hash = {k:v for k,v in hashes.items() if len(v) > 1}
    if dup_hash:
        print("\n[Identische Inhalte (gleicher Hash)]")
        for h, group in dup_hash.items():
            print(f"- {h[:10]}: {group}")

    # Fuzzy-Paare (Namensähnlich)
    print("\n[Ähnliche Dateinamen (potentielle Duplikate / Tippfehler)]")
    reported = set()
    for name in names:
        matches = process.extract(name, names, scorer=fuzz.token_sort_ratio, limit=5)
        for cand, score, _ in matches:
            if cand != name and score >= THRESH:
                pair = tuple(sorted([name, cand]))
                if pair in reported: continue
                reported.add(pair)
                print(f"{score:>3}% :: {pair[0]}  <>  {pair[1]}")
    print("\nHinweis: Prüfe Paare >90%. Entferne Tippfehler-Versionen oder vereinheitliche Schreibweise.")

if __name__ == "__main__":
    main()