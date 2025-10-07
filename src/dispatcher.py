from src.convert_local import extract_text_pymupdf, ocr_pdf_first_page
from src.indexer import add_document

def is_text_pdf(pdf_path: str):
    try:
        t = extract_text_pymupdf(pdf_path)
        return len(t.strip()) > 100, t
    except Exception:
        return False, ""

def process_pdf(doc_id: str, pdf_path: str, meta: dict | None = None):
    meta = meta or {}
    ok, text = is_text_pdf(pdf_path)
    if ok:
        n = add_document(doc_id, text, meta)
        return f"Indexed {n} chunks (text PDF)"
    ocr = ocr_pdf_first_page(pdf_path)  # einfacher Fallback
    if len(ocr.strip()) > 20:
        n = add_document(doc_id, ocr, {**meta, "note": "ocr_first_page"})
        return f"Indexed {n} chunks (scan/ocr)"
    return "No content extracted"
