#!/usr/bin/env python3
"""Text extraction pipeline module."""

import os
import sys
from pathlib import Path
from typing import Iterator

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.convert_local import extract_text_pymupdf

RAW_DIRS_ENV = os.getenv("RAW_DIRS")
if RAW_DIRS_ENV:
    RAW_DIRS = [Path(p).expanduser() for p in RAW_DIRS_ENV.split(os.pathsep) if p.strip()]
else:
    RAW_DIRS = [Path("raw")]

OUT_DIR = Path(os.getenv("TEXT_OUT_DIR", "txt"))
OUT_DIR.mkdir(exist_ok=True, parents=True)


def iter_pdfs() -> Iterator[Path]:
    """Iterate over all PDF files in the raw directories."""
    for base in RAW_DIRS:
        if not base.exists():
            continue
        for pdf in sorted(base.rglob("*.pdf")):
            if pdf.is_file():
                yield pdf


def extract_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file to extract text from
        
    Returns:
        Extracted text content as string, or error message if extraction fails
        
    Note:
        Uses PyMuPDF for text extraction. Returns empty string if no text found,
        or error message prefixed with "[ERROR]" if extraction fails.
    """
    try:
        text = extract_text_pymupdf(str(pdf_path))
        return text if text.strip() else ""
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"


def extract_all_pdfs():
    """
    Extract text from all PDFs in configured directories and save to text files.
    
    Processes all PDF files found in RAW_DIRS (configured directories) and saves
    the extracted text content to corresponding .txt files in the output directory.
    Creates output directory if it doesn't exist.
    
    Note:
        Output files are named as {pdf_name}.txt and saved to the configured
        text output directory. Prints progress information during processing.
    """
    pdfs = list(iter_pdfs())
    if not pdfs:
        print("Keine PDFs gefunden. Setze RAW_DIRS oder lege Dateien unter 'raw/' ab.")
        return
    print(f"Extrahiere Text aus {len(pdfs)} PDFs...")
    for pdf in pdfs:
        out = OUT_DIR / (pdf.stem + ".txt")
        if out.exists():
            continue
        content = extract_pdf(pdf)
        if not content:
            continue
        out.write_text(content, encoding="utf-8")
    print(f"Fertig. Ausgabe in {OUT_DIR}/")