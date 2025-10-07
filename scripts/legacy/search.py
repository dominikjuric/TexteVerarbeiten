#!/usr/bin/env python3
"""Simplified CLI for search functionality that works."""

import argparse
import sys
import os
from pathlib import Path

# Add src to path for imports  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def search_text(query, k=8):
    """Perform text search using Whoosh."""
    try:
        import pipeline.search as psearch
        print(f"🔍 Searching for: '{query}'")
        results = psearch.search_whoosh(query, k)
        
        if not results:
            print("No results found.")
            return
            
        print(f"Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result['filename']}")
            if 'preview' in result:
                print(f"    Preview: {result['preview']}")
            print()
    except Exception as e:
        print(f"Error in text search: {e}")

def search_formulas(symbol=None, contains=None, limit=10):
    """Perform formula search."""
    try:
        import formulas.search as fsearch
        
        if symbol:
            print(f"🔍 Searching formulas with symbol: '{symbol}'")
        elif contains:
            print(f"🔍 Searching formulas containing: '{contains}'")
        else:
            print("Error: Specify either --symbol or --contains")
            return
            
        results = fsearch.search_formulas(symbol, contains, limit)
        
        if not results:
            print("No formula results found.")
            return
            
        print(f"Found {len(results)} formula results:\n")
        for i, result in enumerate(results, 1):
            latex_preview = result['latex'][:120]
            print(f"[{i}] {result['doc_id']}")
            print(f"    LaTeX: {latex_preview}")
            if len(result['latex']) > 120:
                print("    [truncated]")
            print()
    except Exception as e:
        print(f"Error in formula search: {e}")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Search in documents and formulas")
    subparsers = parser.add_subparsers(dest='command', help='Search commands')
    
    # Text search
    text_parser = subparsers.add_parser('text', help='Full-text search')
    text_parser.add_argument('--q', required=True, help='Search query')
    text_parser.add_argument('--k', type=int, default=8, help='Number of results')
    
    # Formula search  
    formula_parser = subparsers.add_parser('formula', help='Formula search')
    formula_parser.add_argument('--symbol', help='Symbol/token to search for')
    formula_parser.add_argument('--contains', help='Regex pattern for LaTeX content')
    formula_parser.add_argument('--limit', type=int, default=10, help='Number of results')
    
    args = parser.parse_args()
    
    if args.command == 'text':
        search_text(args.q, args.k)
    elif args.command == 'formula':
        search_formulas(args.symbol, args.contains, args.limit)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()