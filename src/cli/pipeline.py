#!/usr/bin/env python3
"""CLI for pipeline management."""

import argparse
from typing import Dict

from src.pipeline.extract import extract_all_pdfs
from src.pipeline.index import build_whoosh_index
from src.pipeline.logging_utils import setup_pipeline_logging
from src.formulas.extract import extract_all_formulas
from src.formulas.index import create_formula_index
from src.formulas.nougat import process_nougat_batch


def _print_summary(title: str, result: Dict[str, object]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    processed = result.get("processed", result.get("indexed", 0))
    print(f"Verarbeitet: {processed}/{result.get('total', 0)}")

    skipped = result.get("skipped")
    if skipped:
        print(f"Übersprungen: {skipped}")

    metadata_errors = result.get("metadata_errors")
    if metadata_errors:
        print(f"Metadaten-Warnungen: {metadata_errors}")

    errors = result.get("errors")
    if errors:
        print("Fehler:")
        if isinstance(errors, list):
            for entry in errors:
                if isinstance(entry, dict):
                    origin = entry.get("pdf") or entry.get("file") or "unbekannt"
                    print(f"  - {origin}: {entry.get('error')}")
                else:
                    print(f"  - {entry}")
        else:
            print(f"  - {errors}")

    if "total_formulas" in result:
        print(f"Formeln: {result.get('total_formulas')}")
        with_formulas = result.get("documents_with_formulas")
        without_formulas = result.get("documents_without_formulas")
        if with_formulas is not None or without_formulas is not None:
            print(
                "Dokumente mit/ohne Formeln: "
                f"{with_formulas or 0}/{without_formulas or 0}"
            )
        output_file = result.get("output_file")
        if output_file:
            print(f"Metadaten: {output_file}")
        text_dir = result.get("text_dir")
        if text_dir:
            print(f"Texte ohne LaTeX: {text_dir}")

    if "token_mappings" in result:
        print(f"Token-Zuordnungen: {result.get('token_mappings')}")
        db_path = result.get("db_path")
        if db_path:
            print(f"Index: {db_path}")


def main() -> None:
    """Main CLI entry point for pipeline management."""

    parser = argparse.ArgumentParser(description="PDF knowledge pipeline management")
    subparsers = parser.add_subparsers(dest="command", help="Pipeline commands")

    # Full pipeline
    full_parser = subparsers.add_parser("full", help="Run complete pipeline")
    full_parser.add_argument("--skip-nougat", action="store_true", help="Skip Nougat OCR processing")
    full_parser.add_argument("--batch-size", type=int, default=None, help="Number of PDFs per batch")
    full_parser.add_argument(
        "--index-batch-size", type=int, default=None, help="Number of text files per index batch"
    )
    full_parser.add_argument("--overwrite", action="store_true", help="Reprocess existing outputs")
    full_parser.add_argument("--no-progress", action="store_true", help="Disable progress bars")

    # Individual steps
    extract_parser = subparsers.add_parser("extract", help="Extract text from PDFs")
    extract_parser.add_argument("--batch-size", type=int, default=None, help="Number of PDFs per batch")
    extract_parser.add_argument("--overwrite", action="store_true", help="Reprocess existing outputs")
    extract_parser.add_argument("--no-progress", action="store_true", help="Disable progress bars")

    index_parser = subparsers.add_parser("index", help="Build Whoosh search index")
    index_parser.add_argument("--batch-size", type=int, default=None, help="Number of text files per batch")
    index_parser.add_argument("--no-progress", action="store_true", help="Disable progress bars")

    subparsers.add_parser("nougat", help="Run Nougat OCR on PDFs")
    subparsers.add_parser("formulas", help="Extract formulas from Nougat output")
    subparsers.add_parser("formula-index", help="Build formula search index")

    args = parser.parse_args()

    setup_pipeline_logging()

    if args.command == "full":
        print("Running complete pipeline...")

        print("\n1. Extracting text from PDFs...")
        extract_result = extract_all_pdfs(
            batch_size=args.batch_size,
            overwrite=args.overwrite,
            show_progress=not args.no_progress,
        )
        _print_summary("Textextraktion", extract_result)

        print("\n2. Building Whoosh index...")
        index_result = build_whoosh_index(
            batch_size=args.index_batch_size,
            show_progress=not args.no_progress,
        )
        _print_summary("Whoosh-Index", index_result)

        if not args.skip_nougat:
            print("\n3. Running Nougat OCR...")
            nougat_result = process_nougat_batch()
            print(f"Nougat completed: {nougat_result['success']}/{nougat_result['total']} successful")

            print("\n4. Extracting formulas...")
            formula_result = extract_all_formulas(show_progress=not args.no_progress)
            _print_summary("Formel-Extraktion", formula_result)

            print("\n5. Building formula index...")
            formula_index = create_formula_index()
            _print_summary("Formel-Index", formula_index)
        else:
            print("Skipping Nougat OCR processing")

        print("\nPipeline completed!")

    elif args.command == "extract":
        result = extract_all_pdfs(
            batch_size=args.batch_size,
            overwrite=args.overwrite,
            show_progress=not args.no_progress,
        )
        _print_summary("Textextraktion", result)

    elif args.command == "index":
        result = build_whoosh_index(
            batch_size=args.batch_size,
            show_progress=not args.no_progress,
        )
        _print_summary("Whoosh-Index", result)

    elif args.command == "nougat":
        result = process_nougat_batch()
        print(f"Nougat completed: {result['success']}/{result['total']} successful")

    elif args.command == "formulas":
        result = extract_all_formulas(show_progress=not args.no_progress)
        _print_summary("Formel-Extraktion", result)

    elif args.command == "formula-index":
        result = create_formula_index()
        _print_summary("Formel-Index", result)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

