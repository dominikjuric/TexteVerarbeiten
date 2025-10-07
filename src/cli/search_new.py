#!/usr/bin/env python3
"""CLI for search functionality."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import with absolute path to avoid conflicts
exec("""
from pipeline.search import search_whoosh, print_search_results
""")

# Import functions manually to avoid import conflicts
import pipeline.search as psearch
import formulas.search as fsearch


def main():
    """Main CLI entry point for search."""
    parser = argparse.ArgumentParser(description="Search in documents and formulas")
    subparsers = parser.add_subparsers(dest='command', help='Search commands')
    
    # Text search subcommand
    text_parser = subparsers.add_parser('text', help='Full-text search using Whoosh')
    text_parser.add_argument('--q', required=True, help='Search query')
    text_parser.add_argument('--k', type=int, default=8, help='Number of results')
    
    # Formula search subcommand
    formula_parser = subparsers.add_parser('formula', help='Formula search')
    formula_parser.add_argument('--symbol', help='Symbol/token to search for')
    formula_parser.add_argument('--contains', help='Regex pattern for LaTeX content')
    formula_parser.add_argument('--limit', type=int, default=10, help='Number of results')
    
    # Combined search subcommand
    combined_parser = subparsers.add_parser('combined', help='Combined text and formula search')
    combined_parser.add_argument('--q', required=True, help='Search query')
    combined_parser.add_argument('--k', type=int, default=8, help='Number of text results')
    combined_parser.add_argument('--symbol', help='Formula symbol to search for')
    combined_parser.add_argument('--formula-limit', type=int, default=5, help='Number of formula results')
    
    args = parser.parse_args()
    
    if args.command == 'text':
        results = psearch.search_whoosh(args.q, args.k)
        psearch.print_search_results(results)
        
    elif args.command == 'formula':
        if not args.symbol and not args.contains:
            print("Error: Specify either --symbol or --contains")
            return
        results = fsearch.search_formulas(args.symbol, args.contains, args.limit)
        fsearch.print_formula_results(results)
        
    elif args.command == 'combined':
        print("=== TEXT SEARCH ===")
        text_results = psearch.search_whoosh(args.q, args.k)
        psearch.print_search_results(text_results)
        
        if args.symbol:
            print("\n=== FORMULA SEARCH ===")
            formula_results = fsearch.search_formulas(symbol=args.symbol, limit=args.formula_limit)
            fsearch.print_formula_results(formula_results)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()