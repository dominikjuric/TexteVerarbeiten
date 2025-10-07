#!/usr/bin/env python3
"""CLI for pipeline management."""

import argparse
from src.pipeline.extract import extract_all_pdfs
from src.pipeline.index import build_whoosh_index
from src.formulas.nougat import process_nougat_batch
from src.formulas.extract import extract_all_formulas
from src.formulas.index import create_formula_index


def main():
    """Main CLI entry point for pipeline management."""
    parser = argparse.ArgumentParser(description="PDF knowledge pipeline management")
    subparsers = parser.add_subparsers(dest='command', help='Pipeline commands')
    
    # Full pipeline
    full_parser = subparsers.add_parser('full', help='Run complete pipeline')
    full_parser.add_argument('--skip-nougat', action='store_true', help='Skip Nougat OCR processing')
    
    # Individual steps
    subparsers.add_parser('extract', help='Extract text from PDFs')
    subparsers.add_parser('index', help='Build Whoosh search index')
    subparsers.add_parser('nougat', help='Run Nougat OCR on PDFs')
    subparsers.add_parser('formulas', help='Extract formulas from Nougat output')
    subparsers.add_parser('formula-index', help='Build formula search index')
    
    args = parser.parse_args()
    
    if args.command == 'full':
        print("Running complete pipeline...")
        
        print("\n1. Extracting text from PDFs...")
        extract_all_pdfs()
        
        print("\n2. Building Whoosh index...")
        build_whoosh_index()
        
        if not args.skip_nougat:
            print("\n3. Running Nougat OCR...")
            nougat_result = process_nougat_batch()
            print(f"Nougat completed: {nougat_result['success']}/{nougat_result['total']} successful")
            
            print("\n4. Extracting formulas...")
            formula_result = extract_all_formulas()
            print(f"Extracted {formula_result['total_formulas']} formulas")
            
            print("\n5. Building formula index...")
            create_formula_index()
        else:
            print("Skipping Nougat OCR processing")
        
        print("\nPipeline completed!")
    
    elif args.command == 'extract':
        extract_all_pdfs()
    
    elif args.command == 'index':
        build_whoosh_index()
    
    elif args.command == 'nougat':
        result = process_nougat_batch()
        print(f"Nougat completed: {result['success']}/{result['total']} successful")
    
    elif args.command == 'formulas':
        result = extract_all_formulas()
        print(f"Extracted {result['total_formulas']} formulas")
    
    elif args.command == 'formula-index':
        create_formula_index()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()