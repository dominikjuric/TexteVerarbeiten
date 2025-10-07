from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def extract_text_pymupdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) not available. Install with: pip install PyMuPDF")
    
    doc = fitz.open(pdf_path)
    out = []
    for p in doc:
        t = p.get_text("text")
        if t.strip():
            out.append(t)
    return "\n".join(out)

def ocr_pdf_first_page(pdf_path: str) -> str:
    """OCR first page of PDF using Tesseract."""
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) or pytesseract not available")

    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang="deu+eng")


def _normalize_pdf_date(value: Optional[str]) -> Optional[str]:
    """Convert PDF metadata date strings into ISO format when possible."""

    if not value:
        return None

    cleaned = value.strip()
    if cleaned.startswith("D:"):
        cleaned = cleaned[2:]

    try:
        parsed = datetime.strptime(cleaned[:14], "%Y%m%d%H%M%S")
        return parsed.isoformat()
    except ValueError:
        return value


def extract_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Return structured metadata for ``pdf_path`` using PyMuPDF."""

    if not PYMUPDF_AVAILABLE:
        raise ImportError(
            "PyMuPDF (fitz) not available. Install with: pip install PyMuPDF"
        )

    pdf = Path(pdf_path)
    stats = pdf.stat()

    with fitz.open(pdf_path) as doc:
        metadata = doc.metadata or {}
        pages = doc.page_count
        is_encrypted = doc.is_encrypted

    return {
        "title": metadata.get("title") or pdf.stem,
        "author": metadata.get("author"),
        "subject": metadata.get("subject"),
        "keywords": metadata.get("keywords"),
        "creator": metadata.get("creator"),
        "producer": metadata.get("producer"),
        "creation_date": _normalize_pdf_date(metadata.get("creationDate")),
        "modification_date": _normalize_pdf_date(metadata.get("modDate")),
        "page_count": pages,
        "is_encrypted": is_encrypted,
        "file_size": stats.st_size,
        "absolute_path": str(pdf.resolve()),
    }
