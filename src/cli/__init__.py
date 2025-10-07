"""Command-line interfaces for the PDF knowledge pipeline."""

from .extract import main as extract_main
from .search import main as search_main
from .analyze import main as analyze_main
from .pipeline import main as pipeline_main

__all__ = [
    'extract_main',
    'search_main',
    'analyze_main',
    'pipeline_main'
]