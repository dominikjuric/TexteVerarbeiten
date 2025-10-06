#!/usr/bin/env python3
import re, json, hashlib
from pathlib import Path

MD_DIR = Path("processed/nougat_md")
OUT_TEXT_DIR = Path("txt_nougat")
OUT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
FORMULA_JSONL = Path("metadata/formulas.jsonl")
FORMULA_JSONL.parent.mkdir(parents=True, exist_ok=True)

FORMULA_BLOCK = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
FORMULA_INLINE = re.compile(r'(?<!\$)\$(.+?)\$(?!\$)')

def norm_formula(f):
    # einfache Normierung: Trim + mehrere Spaces raus
    return re.sub(r'\s+',' ', f.strip())

def hash_formula(f):
    return hashlib.md5(f.encode('utf-8')).hexdigest()[:12]

def process_md(md_path: Path, formulas_out):
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    doc_id = md_path.stem

    # Reihenfolge: Block-Formeln zuerst
    replaced = text
    # Block
    for match in FORMULA_BLOCK.finditer(text):
        original = match.group(0)
        inner = norm_formula(match.group(1))
        h = hash_formula(inner)
        placeholder = f" FORMULA_{h} "
        replaced = replaced.replace(original, placeholder)
        formulas_out.append({"doc_id": doc_id, "hash": h, "type": "block", "latex": inner})

    # Inline
    for match in FORMULA_INLINE.finditer(text):
        original = match.group(0)
        inner = norm_formula(match.group(1))
        h = hash_formula(inner)
        placeholder = f" FORMULA_{h} "
        replaced = replaced.replace(original, placeholder)
        formulas_out.append({"doc_id": doc_id, "hash": h, "type": "inline", "latex": inner})

    # Speichere reinen Text (Markdown ohne Rohformeln, Platzhalter statt LaTeX)
    (OUT_TEXT_DIR / f"{doc_id}.txt").write_text(replaced, encoding="utf-8")

def main():
    formulas_out = []
    for md in MD_DIR.glob("*.md"):
        process_md(md, formulas_out)
    with FORMULA_JSONL.open("w", encoding="utf-8") as f:
        for row in formulas_out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Formeln extrahiert: {len(formulas_out)} → {FORMULA_JSONL}")

if __name__ == "__main__":
    main()