#!/usr/bin/env python3
from pathlib import Path
from pypdf import PdfReader
import re

RAW_DIRS = [Path("raw/Paper"), Path("raw/Bücher")]
OUT_DIR = Path("txt")
OUT_DIR.mkdir(exist_ok=True, parents=True)

def clean(text: str):
    # Minimale Normalisierung
    text = text.replace('\u00ad','')  # Soft hyphen
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_pdf(pdf_path: Path):
    try:
        reader = PdfReader(str(pdf_path))
        pages = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            pages.append(f"[PAGE {i+1}]\n{clean(txt)}")
        return "\n\n".join(pages)
    except Exception as e:
        return f"[ERROR] {e}"

def main():
    pdfs = []
    for d in RAW_DIRS:
        if d.exists():
            pdfs.extend(list(d.glob("*.pdf")))
    print(f"Extrahiere Text aus {len(pdfs)} PDFs...")
    for p in pdfs:
        out = OUT_DIR / (p.stem + ".txt")
        if out.exists(): 
            continue
        content = extract_pdf(p)
        out.write_text(content, encoding="utf-8")
    print("Fertig. Ausgabe in txt/")

if __name__ == "__main__":
    main()