"""PDF Knowledge Pipeline - Restructured modular architecture.

This package provides a complete pipeline for processing PDF documents:
- Text extraction from PDFs
- Full-text search indexing
- OCR with Nougat for mathematical formulas
- Formula extraction and search
- Duplicate detection and relevance analysis

Note: To keep imports lightweight and avoid side effects, we do not import
subpackages at module import time. Import the needed submodules explicitly, e.g.:

    from src.formulas import nougat_processor
    from src.core import embedding_store

This prevents unrelated import errors from breaking `import src`.
"""

__version__ = "1.0.0"

# Public subpackages (names for discoverability only)
# Import subpackages explicitly in your code as needed
from typing import List

__all__: List[str] = []