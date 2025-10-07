#!/usr/bin/env python3
"""CLI for text extraction from PDFs."""

import argparse
from src.pipeline.extract import extract_all_pdfs


def main():
    """Main CLI entry point for text extraction."""
    parser = argparse.ArgumentParser(description="Extract text from PDFs")
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print("Starting PDF text extraction...")
    
    extract_all_pdfs()


if __name__ == "__main__":
    main()