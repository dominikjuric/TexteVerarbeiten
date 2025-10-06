#!/usr/bin/env python3
from pathlib import Path
from io import StringIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

RAW_DIRS = [Path("raw/Paper"), Path("raw/Bücher")]
OUT_DIR = Path("txt_pdfminer")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_pdfminer(pdf_path: Path):
    output = StringIO()
    try:
        with open(pdf_path, 'rb') as f:
            laparams = LAParams(line_margin=0.2, char_margin=2.0, word_margin=0.1)
            extract_text_to_fp(f, output, laparams=laparams, output_type='text', codec='utf-8')
        return output.getvalue()
    except Exception as e:
        return f"[ERROR] {e}"

def main():
    pdfs = []
    for d in RAW_DIRS:
        if d.exists():
            pdfs.extend(d.glob("*.pdf"))
    print(f"pdfminer Extraktion für {len(pdfs)} PDFs...")
    for p in pdfs:
        out = OUT_DIR / (p.stem + ".txt")
        if out.exists():
            continue
        txt = extract_pdfminer(p)
        out.write_text(txt, encoding="utf-8", errors="ignore")
    print("Fertig: txt_pdfminer/")

if __name__ == "__main__":
    main()