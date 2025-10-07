#!/usr/bin/env python3
"""Formula extraction from Nougat markdown files."""

import re
import json
import hashlib
from pathlib import Path

MD_DIR = Path("processed/nougat_md")
OUT_TEXT_DIR = Path("txt_nougat")
OUT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
FORMULA_JSONL = Path("metadata/formulas.jsonl")
FORMULA_JSONL.parent.mkdir(parents=True, exist_ok=True)

FORMULA_BLOCK = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
FORMULA_INLINE = re.compile(r'(?<!\$)\$(.+?)\$(?!\$)')


def norm_formula(f: str) -> str:
    """Normalize formula by trimming and removing extra spaces."""
    return re.sub(r'\s+', ' ', f.strip())


def hash_formula(f: str) -> str:
    """Generate a short hash for a formula."""
    return hashlib.md5(f.encode('utf-8')).hexdigest()[:12]


def extract_formulas_from_md(md_path: Path) -> tuple[str, list[dict]]:
    """Extract formulas from markdown file and return processed text."""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    doc_id = md_path.stem
    formulas = []

    # Process text to replace formulas with placeholders
    replaced = text
    
    # Block formulas first
    for match in FORMULA_BLOCK.finditer(text):
        original = match.group(0)
        inner = norm_formula(match.group(1))
        h = hash_formula(inner)
        placeholder = f" FORMULA_{h} "
        replaced = replaced.replace(original, placeholder)
        formulas.append({
            "doc_id": doc_id, 
            "hash": h, 
            "type": "block", 
            "latex": inner
        })

    # Inline formulas
    for match in FORMULA_INLINE.finditer(text):
        original = match.group(0)
        inner = norm_formula(match.group(1))
        h = hash_formula(inner)
        placeholder = f" FORMULA_{h} "
        replaced = replaced.replace(original, placeholder)
        formulas.append({
            "doc_id": doc_id, 
            "hash": h, 
            "type": "inline", 
            "latex": inner
        })

    return replaced, formulas


def process_all_markdown_files() -> list[dict]:
    """Process all markdown files and extract formulas."""
    all_formulas = []
    md_files = list(MD_DIR.glob("*.md")) + list(MD_DIR.glob("*.mmd"))
    
    print(f"Processing {len(md_files)} markdown files...")
    
    for md_path in md_files:
        replaced_text, formulas = extract_formulas_from_md(md_path)
        all_formulas.extend(formulas)
        
        # Save processed text (markdown without raw formulas)
        out_file = OUT_TEXT_DIR / f"{md_path.stem}.txt"
        out_file.write_text(replaced_text, encoding="utf-8")
    
    return all_formulas


def save_formulas_jsonl(formulas: list[dict]) -> Path:
    """Save formulas to JSONL file."""
    with FORMULA_JSONL.open("w", encoding="utf-8") as f:
        for row in formulas:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return FORMULA_JSONL


def extract_all_formulas() -> dict:
    """Extract all formulas from markdown files."""
    formulas = process_all_markdown_files()
    output_file = save_formulas_jsonl(formulas)
    
    print(f"Formeln extrahiert: {len(formulas)} → {output_file}")
    
    return {
        'total_formulas': len(formulas),
        'output_file': output_file,
        'text_dir': OUT_TEXT_DIR,
        'formulas': formulas
    }