#!/usr/bin/env python3
"""
PDF Pipeline CLI

Command-line interface for the PDF processing pipeline.
Supports single PDF processing and semantic search.

Usage:
    python pipeline_cli.py process --pdf path/to/file.pdf
    python pipeline_cli.py search --query "your search terms"
    python pipeline_cli.py stats
"""

import argparse
import logging
import os
from pathlib import Path
import time

# Constants
ERROR_EMBEDDING_STORE_CREATION = "❌ Could not create embedding store"

# Set up clean environment
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Set up logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(levelname)s: %(message)s'
)

def process_pdf(pdf_path: str, use_nougat: bool = False):
    """Process a single PDF through the pipeline."""
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return False
    
    print(f"📄 Processing: {pdf_file.name}")
    
    try:
        from src.core.dispatcher import create_dispatcher, ProcessingEngine, DocumentRoute
        from src.core.embedding_store import create_embedding_store
        
        from src.formulas.nougat_processor import check_nougat_cli
        
        # Create dispatcher
        dispatcher = create_dispatcher()
        if not dispatcher:
            print("❌ Could not create dispatcher")
            return False
        
        # Analyze document for routing
        route = None
        if use_nougat:
            try:
                nougat_available = check_nougat_cli()
            except Exception:
                nougat_available = False
            if nougat_available:
                route = DocumentRoute(
                    engine=ProcessingEngine.NOUGAT,
                    confidence=0.9,
                    reason="User requested Nougat"
                )
                print("🧠 Using Nougat OCR")
            else:
                print("⚠️ Nougat CLI not available, falling back to automatic routing.")

        if route is None:
            route = dispatcher.analyze_document(pdf_file)
            print(f"🔧 Using {route.engine.value} (confidence: {route.confidence:.2f})")
        
        # Process document
        result = dispatcher.process_document(pdf_file, route)
        
        if not result.success:
            print(f"❌ Processing failed: {result.error_message}")
            return False
        
        print(f"✅ Extracted {len(result.text)} characters in {result.processing_time:.2f}s")
        
        # Add to ChromaDB
        store = create_embedding_store()
        if not store:
            print(ERROR_EMBEDDING_STORE_CREATION)
            return False
            
        doc_id = f"{pdf_file.stem}_{int(time.time())}"
        metadata = {
            "source": str(pdf_file),
            "engine": result.engine_used.value,
            "filename": pdf_file.name,
            "processing_time": result.processing_time
        }
        
        print("💾 Adding to knowledge base...")
        doc_ids = store.add_documents([result.text], [metadata], [doc_id])
        print(f"✅ Added as: {doc_ids[0]}")
        
        # Show preview
        preview_lines = result.text.split('\n')[:3]
        print("\n📖 Content preview:")
        for line in preview_lines:
            if line.strip():
                print(f"   {line[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return False


def search_knowledge_base(query: str, limit: int = 5):
    """Search the knowledge base."""
    print(f"🔍 Searching for: '{query}'")
    
    try:
        from src.core.embedding_store import create_embedding_store
        
        store = create_embedding_store()
        if not store:
            print(ERROR_EMBEDDING_STORE_CREATION)
            return False
            
        results = store.similarity_search(query, k=limit)
        
        if not results:
            print("❌ No results found")
            return False
        
        print(f"\n📊 Found {len(results)} results:")
        print("-" * 50)
        
        for i, result in enumerate(results, 1):
            distance = result.get('distance', 1.0)
            content = result.get('document', '')
            metadata = result.get('metadata', {})
            
            # Score (lower distance = better match)
            score_percent = max(0, (1.0 - distance) * 100)
            
            print(f"{i}. Score: {score_percent:.1f}%")
            print(f"   Source: {metadata.get('filename', 'Unknown')}")
            print(f"   Engine: {metadata.get('engine', 'Unknown')}")
            
            # Content preview
            content_lines = content.split('\n')[:2]
            for line in content_lines:
                if line.strip():
                    print(f"   {line[:100]}...")
                    break
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False


def show_stats():
    """Show knowledge base statistics."""
    print("📊 Knowledge Base Statistics")
    print("-" * 30)
    
    try:
        from src.core.embedding_store import create_embedding_store
        
        store = create_embedding_store()
        if not store:
            print(ERROR_EMBEDDING_STORE_CREATION)
            return False
            
        stats = store.get_collection_stats()
        
        print(f"Documents: {stats['document_count']}")
        print(f"Model: {stats['embedding_model']}")
        print(f"Storage: {stats['persist_directory']}")
        
        # Check if Nougat is available
        from src.core.dispatcher import create_dispatcher
        dispatcher = create_dispatcher()
        if dispatcher:
            nougat_available = dispatcher.check_nougat_availability()
            print(f"Nougat OCR: {'✅ Available' if nougat_available else '❌ Not available'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="PDF Processing Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline_cli.py process --pdf paper.pdf
  python pipeline_cli.py process --pdf paper.pdf --nougat
  python pipeline_cli.py search --query "machine learning" 
  python pipeline_cli.py search --query "neural networks" --limit 3
  python pipeline_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process a PDF file')
    process_parser.add_argument('--pdf', required=True, help='Path to PDF file')
    process_parser.add_argument('--nougat', action='store_true', 
                               help='Force use of Nougat OCR (for scientific papers)')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search the knowledge base')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--limit', type=int, default=5, 
                              help='Maximum number of results (default: 5)')
    
    # Stats command
    subparsers.add_parser('stats', help='Show knowledge base statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    print("🚀 PDF Processing Pipeline")
    print("=" * 40)
    
    success = False
    
    if args.command == 'process':
        success = process_pdf(args.pdf, args.nougat)
    elif args.command == 'search':
        success = search_knowledge_base(args.query, args.limit)
    elif args.command == 'stats':
        success = show_stats()
    
    if success:
        print("\n✅ Command completed successfully")
        return 0
    else:
        print("\n❌ Command failed")
        return 1


if __name__ == "__main__":
    exit(main())