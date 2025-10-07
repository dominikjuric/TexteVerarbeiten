"""Compatibility wrappers for Nougat OCR helpers.

This module re-exports the functionality from ``nougat_processor`` to avoid code
duplication. Prefer importing directly from ``src.formulas.nougat_processor``.
"""

from .nougat_processor import (
    NOUGAT_MODEL_BASE,
    NOUGAT_MODEL_SMALL,
    NougatProcessor,
    check_nougat_cli,
    create_nougat_processor,
    get_pdf_files,
    process_nougat_batch,
    process_pdf_with_nougat,
    run_nougat_single,
)

__all__ = [
    "NOUGAT_MODEL_BASE",
    "NOUGAT_MODEL_SMALL",
    "NougatProcessor",
    "check_nougat_cli",
    "create_nougat_processor",
    "get_pdf_files",
    "process_nougat_batch",
    "process_pdf_with_nougat",
    "run_nougat_single",
]
