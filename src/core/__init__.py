"""Core functionality for the PDF knowledge pipeline."""

# Import only basic functions to avoid dependency issues
try:
    from .convert_local import extract_text_pymupdf, ocr_pdf_first_page
    CONVERT_AVAILABLE = True
except ImportError:
    CONVERT_AVAILABLE = False
    extract_text_pymupdf = None
    ocr_pdf_first_page = None

try:
    from .indexer import add_document, purge_by_source, chunk
    INDEXER_AVAILABLE = True
except ImportError:
    INDEXER_AVAILABLE = False
    add_document = None
    purge_by_source = None
    chunk = None

# Skip RAG import due to numpy compatibility issues
# from .rag import ask

__all__ = [
    'extract_text_pymupdf',
    'ocr_pdf_first_page', 
    'add_document',
    'purge_by_source',
    'chunk'
]