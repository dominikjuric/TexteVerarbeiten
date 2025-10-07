try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import io
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