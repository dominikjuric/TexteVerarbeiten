#!/usr/bin/env python3
"""CLI for analysis tools."""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from analysis.duplicates import scan_duplicates
from analysis.relevance import generate_relevance_report


def main():
    """Main CLI entry point for analysis tools."""
    parser = argparse.ArgumentParser(description="Analysis tools for PDF collection")
    subparsers = parser.add_subparsers(dest='command', help='Analysis commands')
    
    # Duplicate detection
    dup_parser = subparsers.add_parser('duplicates', help='Scan for duplicate files')
    dup_parser.add_argument(
        '--threshold', 
        type=int, 
        default=90, 
        help='Similarity threshold for name matching (default: 90)'
    )
    
    # Relevance analysis
    rel_parser = subparsers.add_parser('relevance', help='Generate relevance report')
    rel_parser.add_argument(
        '--keywords', 
        type=str, 
        default="reconstruction,super-resolution,gappy,POD,uncertainty",
        help='Comma-separated keywords to search for'
    )
    
    args = parser.parse_args()
    
    if args.command == 'duplicates':
        result = scan_duplicates()
        if result:
            print(f"\nSummary:")
            print(f"- Total files: {result['total_files']}")
            print(f"- Duplicate hash groups: {len(result['duplicate_hashes'])}")
            print(f"- Similar name pairs: {len(result['similar_names'])}")
    
    elif args.command == 'relevance':
        rows, out_file = generate_relevance_report(args.keywords)
        print(f"\nGenerated relevance report with {len(rows)} documents.")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()