#!/usr/bin/env python3
"""
Complete Pipeline Integration Script

This script demonstrates the full end-to-end pipeline integration:
1. Zotero integration (to_process → processed)
2. Intelligent dispatcher (routes to Nougat for scientific papers)
3. Nougat OCR processing with pages support
4. ChromaDB ingestion and semantic search
5. RAG pipeline (when LangChain issues are resolved)

Run this to see all components working together.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_zotero_integration():
    """Test Zotero client functionality."""
    try:
        from src.core.zotero_client import create_zotero_client
        
        print("🔄 Testing Zotero integration...")
        client = create_zotero_client()
        if not client:
            print("❌ Zotero client not available (check config)")
            return False
        
        # Get items to process
        items = client.get_items_to_process()
        print(f"📚 Found {len(items)} items to process")
        
        return True
        
    except ImportError as e:
        print(f"❌ Zotero import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Zotero test failed: {e}")
        return False


def test_dispatcher():
    """Test intelligent PDF dispatcher."""
    try:
        from src.core.dispatcher import PDFDispatcher, ProcessingEngine
        
        print("\n🔄 Testing PDF dispatcher...")
        dispatcher = PDFDispatcher()
        
        # Test with a scientific PDF
        test_pdf = Path("raw/Deep Reserach GANs.pdf")
        if not test_pdf.exists():
            print("❌ Test PDF not found")
            return False
        
        # Analyze document
        analysis = dispatcher.analyze_document(test_pdf)
        print(f"📊 Analysis: {analysis}")
        
        # Check if Nougat is available
        nougat_available = dispatcher.check_nougat_availability()
        print(f"🧠 Nougat available: {nougat_available}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Dispatcher import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Dispatcher test failed: {e}")
        return False


def test_nougat_processing():
    """Test Nougat OCR with pages support."""
    try:
        from src.formulas.nougat_processor import create_nougat_processor
        
        print("\n🔄 Testing Nougat processing...")
        processor = create_nougat_processor()
        if not processor:
            print("❌ Nougat processor not available")
            return False
        
        test_pdf = Path("raw/Deep Reserach GANs.pdf")
        if not test_pdf.exists():
            print("❌ Test PDF not found")
            return False
        
        # Check if already processed
        output_file = Path("processed/nougat_md/Deep Reserach GANs.mmd")
        if output_file.exists():
            print(f"✅ Using existing Nougat output: {output_file}")
            content = output_file.read_text(encoding='utf-8')
            print(f"📄 Content length: {len(content)} characters")
            return True
        
        # Process with pages limit for speed
        print("🚀 Processing first 3 pages with Nougat...")
        result = processor.process_pdf(test_pdf, pages="1-3")
        
        if result['success']:
            print(f"✅ Nougat processing successful!")
            print(f"📄 Output: {result['output_path']}")
            print(f"⏱️ Time: {result['processing_time']:.2f}s")
            return True
        else:
            print(f"❌ Nougat processing failed: {result['error']}")
            return False
            
    except ImportError as e:
        print(f"❌ Nougat import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Nougat test failed: {e}")
        return False


def test_chromadb_integration():
    """Test ChromaDB embedding and search."""
    try:
        from src.core.embedding_store import create_embedding_store
        
        print("\n🔄 Testing ChromaDB integration...")
        store = create_embedding_store()
        
        # Check if we have Nougat output to ingest
        nougat_file = Path("processed/nougat_md/Deep Reserach GANs.mmd")
        if not nougat_file.exists():
            print("❌ No Nougat output found for ingestion")
            return False
        
        # Get current stats
        stats = store.get_collection_stats()
        print(f"📊 Current collection: {stats}")
        
        # Add document if not already present
        if stats['document_count'] == 0:
            content = nougat_file.read_text(encoding='utf-8')
            metadata = {
                "source": str(nougat_file),
                "doc_type": "nougat_ocr",
                "pages": "1-3",
                "format": "mmd"
            }
            
            doc_ids = store.add_documents([content], [metadata], ["deep_research_gans"])
            print(f"✅ Added document: {doc_ids}")
        
        # Test semantic search
        queries = ["expectation values GANs", "mathematical probability"]
        for query in queries:
            print(f"\n🔍 Query: '{query}'")
            results = store.similarity_search(query, k=2)
            for i, result in enumerate(results):
                distance = result.get('distance', 'N/A')
                content_preview = result.get('document', '')[:80]
                print(f"  {i+1}. Score: {distance} - {content_preview}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ ChromaDB import error: {e}")
        return False
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False


def test_rag_pipeline():
    """Test RAG pipeline (if LangChain is working)."""
    try:
        from src.core.rag_pipeline import RAGPipeline, create_rag_pipeline
        
        print("\n🔄 Testing RAG pipeline...")
        
        # Try to create RAG pipeline
        rag = create_rag_pipeline()
        if not rag:
            print("⚠️ RAG pipeline not available (LangChain API issues)")
            return False
        
        # Test query
        response = rag.query("What are expectation values in GANs?")
        print(f"🤖 RAG Response: {response}")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ RAG not available: {e}")
        return False
    except Exception as e:
        print(f"⚠️ RAG test failed: {e}")
        return False


def run_integration_test():
    """Run complete integration test."""
    print("🚀 Starting Complete Pipeline Integration Test")
    print("=" * 60)
    
    # Track results
    test_results = {
        "zotero": False,
        "dispatcher": False,
        "nougat": False,
        "chromadb": False,
        "rag": False
    }
    
    # Run tests in order
    test_results["zotero"] = test_zotero_integration()
    test_results["dispatcher"] = test_dispatcher()
    test_results["nougat"] = test_nougat_processing()
    test_results["chromadb"] = test_chromadb_integration()
    test_results["rag"] = test_rag_pipeline()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    for component, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{component.ljust(15)}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} components working")
    
    if passed_tests >= 3:  # Core components working
        print("🎉 Core pipeline is functional!")
        print("\nNext steps:")
        if not test_results["zotero"]:
            print("- Configure Zotero API credentials")
        if not test_results["rag"]:
            print("- Fix LangChain API compatibility issues")
        print("- Add more PDFs for testing")
        print("- Implement batch processing")
    else:
        print("⚠️ Pipeline needs more work before full deployment")
    
    return passed_tests >= 3


if __name__ == "__main__":
    success = run_integration_test()
    exit(0 if success else 1)