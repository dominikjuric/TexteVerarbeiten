import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

def extract_text_pymupdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    out = []
    for p in doc:
        t = p.get_text("text")
        if t.strip(): out.append(t)
    return "\n".join(out)

def ocr_pdf_first_page(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang="deu+eng")
