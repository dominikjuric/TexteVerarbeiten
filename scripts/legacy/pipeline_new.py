#!/usr/bin/env python3
"""Main pipeline script using the restructured modular architecture."""

import argparse
import json
from pathlib import Path

from src.pipeline.extract import extract_all_pdfs
from src.pipeline.index import build_whoosh_index
from src.formulas.nougat import process_nougat_batch
from src.formulas.extract import extract_all_formulas
from src.formulas.index import create_formula_index
from src.analysis.duplicates import scan_duplicates
from src.analysis.relevance import generate_relevance_report

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config():
    """Load configuration from config.json."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return json.load(f)
    return {}


def ensure_dirs(cfg):
    """Ensure required directories exist."""
    if "directories" in cfg:
        for d in cfg["directories"].values():
            Path(d).mkdir(parents=True, exist_ok=True)


def run_full_pipeline(skip_nougat=False):
    """Run the complete PDF processing pipeline."""
    print("Starting PDF Knowledge Pipeline...")
    
    cfg = load_config()
    ensure_dirs(cfg)
    
    # Step 1: Extract text from PDFs
    print("\n1. Extracting text from PDFs...")
    extract_all_pdfs()
    
    # Step 2: Build Whoosh search index
    print("\n2. Building Whoosh search index...")
    build_whoosh_index()
    
    # Step 3: Duplicate detection
    print("\n3. Scanning for duplicates...")
    dup_result = scan_duplicates()
    if dup_result:
        print(f"Found {len(dup_result['duplicate_hashes'])} duplicate groups")
    
    # Step 4: Relevance analysis
    print("\n4. Generating relevance report...")
    generate_relevance_report()
    
    if not skip_nougat:
        # Step 5: Nougat OCR processing
        print("\n5. Running Nougat OCR...")
        nougat_result = process_nougat_batch()
        print(f"Nougat: {nougat_result['success']}/{nougat_result['total']} successful")
        
        # Step 6: Extract formulas
        print("\n6. Extracting formulas...")
        formula_result = extract_all_formulas()
        print(f"Extracted {formula_result['total_formulas']} formulas")
        
        # Step 7: Build formula index
        print("\n7. Building formula search index...")
        create_formula_index()
    else:
        print("Skipping Nougat OCR processing (--skip-nougat)")
    
    print("\nPipeline completed successfully!")


def main():
    """Main entry point for the pipeline script."""
    parser = argparse.ArgumentParser(
        description="PDF Knowledge Pipeline - Complete document processing system"
    )
    
    parser.add_argument(
        '--skip-nougat', 
        action='store_true',
        help='Skip Nougat OCR processing (faster, but no formula extraction)'
    )
    
    parser.add_argument(
        '--step',
        choices=['extract', 'index', 'duplicates', 'relevance', 'nougat', 'formulas', 'formula-index'],
        help='Run only a specific pipeline step'
    )
    
    args = parser.parse_args()
    
    if args.step:
        # Run individual steps
        if args.step == 'extract':
            extract_all_pdfs()
        elif args.step == 'index':
            build_whoosh_index()
        elif args.step == 'duplicates':
            scan_duplicates()
        elif args.step == 'relevance':
            generate_relevance_report()
        elif args.step == 'nougat':
            result = process_nougat_batch()
            print(f"Nougat: {result['success']}/{result['total']} successful")
        elif args.step == 'formulas':
            result = extract_all_formulas()
            print(f"Extracted {result['total_formulas']} formulas")
        elif args.step == 'formula-index':
            create_formula_index()
    else:
        # Run full pipeline
        run_full_pipeline(skip_nougat=args.skip_nougat)


if __name__ == "__main__":
    main()