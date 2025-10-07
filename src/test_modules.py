#!/usr/bin/env python3
"""Test script to check which modules are working."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent
sys.path.append(str(src_path))

def test_analysis():
    """Test analysis modules."""
    try:
        from analysis.duplicates import scan_duplicates
        from analysis.relevance import generate_relevance_report
        print("✅ Analysis modules: OK")
        return True
    except Exception as e:
        print(f"❌ Analysis modules: {e}")
        return False

def test_formulas():
    """Test formula modules."""
    try:
        from formulas.extract import extract_all_formulas
        from formulas.search import search_formulas
        print("✅ Formula modules: OK")
        return True
    except Exception as e:
        print(f"❌ Formula modules: {e}")
        return False

def test_pipeline():
    """Test pipeline modules."""
    try:
        from pipeline.extract import extract_all_pdfs
        print("✅ Pipeline extract: OK")
        pipeline_extract_ok = True
    except Exception as e:
        print(f"❌ Pipeline extract: {e}")
        pipeline_extract_ok = False
    
    try:
        from pipeline.index import build_whoosh_index
        print("✅ Pipeline index: OK (needs Whoosh dependency)")
        pipeline_index_ok = True
    except Exception as e:
        print(f"❌ Pipeline index: {e}")
        pipeline_index_ok = False
    
    try:
        from pipeline.search import search_whoosh
        print("✅ Pipeline search: OK (needs Whoosh dependency)")
        pipeline_search_ok = True
    except Exception as e:
        print(f"❌ Pipeline search: {e}")
        pipeline_search_ok = False
    
    return pipeline_extract_ok or pipeline_index_ok or pipeline_search_ok

def test_core():
    """Test core modules."""
    try:
        from core.convert_local import extract_text_pymupdf
        print("✅ Core convert: OK (will warn about PyMuPDF)")
    except Exception as e:
        print(f"❌ Core convert: {e}")
        return False
    
    try:
        from core.indexer import add_document
        print("✅ Core indexer: OK (will warn about dependencies)")
    except Exception as e:
        print(f"❌ Core indexer: {e}")
        return False
    
    try:
        from core.rag import ask
        print("✅ Core RAG: OK (will warn about dependencies)")
        return True
    except Exception as e:
        print(f"❌ Core RAG: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing restructured PDF pipeline modules...\n")
    
    results = []
    results.append(test_analysis())
    results.append(test_formulas()) 
    results.append(test_pipeline())
    results.append(test_core())
    
    working = sum(results)
    total = len(results)
    
    print(f"\n📊 Summary: {working}/{total} module groups working")
    
    if working == total:
        print("🎉 All module groups load successfully!")
        print("Note: Some modules will need dependencies installed to run fully.")
    else:
        print("⚠️  Some modules have issues. Check dependencies.")

if __name__ == "__main__":
    main()