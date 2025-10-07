#!/usr/bin/env python3
"""
End-to-End Pipeline Test

Tests the complete workflow:
1. PDF → Dispatcher → Nougat → Markdown
2. Markdown → ChromaDB → Semantic Search
3. Validation of full pipeline
"""

import logging
from pathlib import Path
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_end_to_end_pipeline():
    """Test complete pipeline from PDF to searchable knowledge base."""
    
    print("🚀 Starting End-to-End Pipeline Test")
    print("=" * 60)
    
    # Test PDF
    test_pdf = Path("raw/Deep Reserach GANs.pdf")
    if not test_pdf.exists():
        print("❌ Test PDF not found")
        return False
    
    print(f"📄 Testing with: {test_pdf.name}")
    
    # Step 1: Test Dispatcher with Nougat Integration
    print("\n🔄 Step 1: Testing Dispatcher → Nougat Integration")
    try:
        from src.core.dispatcher import create_dispatcher, ProcessingEngine
        
        dispatcher = create_dispatcher()
        if not dispatcher:
            print("❌ Could not create dispatcher")
            return False
        
        # Check Nougat availability
        nougat_available = dispatcher.check_nougat_availability()
        print(f"🧠 Nougat available: {nougat_available}")
        
        if not nougat_available:
            print("❌ Nougat not available in dispatcher")
            return False
        
        # Analyze document for routing
        route = dispatcher.analyze_document(test_pdf)
        print(f"📊 Routing decision: {route.engine.value} (confidence: {route.confidence})")
        print(f"📝 Reason: {route.reason}")
        
        # Force Nougat for this test
        if route.engine != ProcessingEngine.NOUGAT:
            print("⚠️ Document not routed to Nougat, forcing Nougat for test...")
            from src.core.dispatcher import DocumentRoute
            route = DocumentRoute(
                engine=ProcessingEngine.NOUGAT,
                confidence=0.9,
                reason="Forced for end-to-end test"
            )
        
        # Process document
        print("🔬 Processing with Nougat...")
        start_time = time.time()
        result = dispatcher.process_document(test_pdf, route)
        process_time = time.time() - start_time
        
        if not result.success:
            print(f"❌ Processing failed: {result.error_message}")
            return False
        
        print(f"✅ Processing successful! ({process_time:.2f}s)")
        print(f"📄 Text length: {len(result.text)} characters")
        print(f"🔧 Engine used: {result.engine_used.value}")
        
        # Preview
        lines = result.text.split('\n')[:5]
        print("📖 Preview:")
        for line in lines:
            if line.strip():
                print(f"   {line}")
        
    except Exception as e:
        print(f"❌ Dispatcher test failed: {e}")
        return False
    
    # Step 2: Test ChromaDB Integration
    print("\n🔄 Step 2: Testing ChromaDB Integration")
    try:
        from src.core.embedding_store import create_embedding_store
        
        store = create_embedding_store()
        if not store:
            print("❌ Could not create embedding store")
            return False
        
        # Add processed text to ChromaDB
        doc_id = f"test_end_to_end_{int(time.time())}"
        metadata = {
            "source": str(test_pdf),
            "engine": result.engine_used.value,
            "processing_time": result.processing_time,
            "test_run": True
        }
        
        print("💾 Adding to ChromaDB...")
        doc_ids = store.add_documents([result.text], [metadata], [doc_id])
        print(f"✅ Added document: {doc_ids[0]}")
        
        # Test semantic search
        queries = [
            "expectation values",
            "GANs probability",
            "mathematical formulas"
        ]
        
        print("\n🔍 Testing semantic search:")
        for query in queries:
            results = store.similarity_search(query, k=1)
            if results:
                distance = results[0].get('distance', 1.0)
                content = results[0].get('document', '')[:100]
                print(f"  '{query}' → Score: {distance:.3f} - {content}...")
            else:
                print(f"  '{query}' → No results")
        
        # Collection stats
        stats = store.get_collection_stats()
        print(f"📊 Collection stats: {stats['document_count']} documents")
        
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False
    
    # Step 3: Performance Summary
    print("\n📈 Performance Summary")
    print("=" * 40)
    print(f"PDF Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Text Extracted: {len(result.text)} characters")
    print(f"Engine Used: {result.engine_used.value}")
    print(f"Words per Second: {len(result.text.split()) / max(result.processing_time, 0.1):.1f}")
    
    print("\n✅ End-to-End Pipeline Test SUCCESSFUL!")
    print("\n🎯 Next Steps:")
    print("- Add batch processing for multiple PDFs")
    print("- Implement simple RAG queries")
    print("- Add CLI interface for easy use")
    
    return True


def test_batch_processing():
    """Test batch processing of multiple PDFs."""
    print("\n🔄 Testing Batch Processing")
    
    # Find available PDFs
    raw_dir = Path("raw")
    pdfs = list(raw_dir.glob("*.pdf"))[:3]  # Test with first 3 PDFs
    
    if not pdfs:
        print("❌ No PDFs found for batch test")
        return False
    
    print(f"📚 Found {len(pdfs)} PDFs for batch test")
    
    try:
        from src.core.dispatcher import create_dispatcher
        
        dispatcher = create_dispatcher()
        batch_results = []
        
        for pdf in pdfs:
            print(f"\n📄 Processing: {pdf.name}")
            
            # Analyze and process
            route = dispatcher.analyze_document(pdf)
            result = dispatcher.process_document(pdf, route)
            
            batch_results.append({
                'pdf': pdf.name,
                'success': result.success,
                'engine': result.engine_used.value,
                'text_length': len(result.text),
                'time': result.processing_time
            })
            
            status = "✅" if result.success else "❌"
            print(f"  {status} {result.engine_used.value} ({result.processing_time:.1f}s)")
        
        # Summary
        successful = sum(1 for r in batch_results if r['success'])
        total_time = sum(r['time'] for r in batch_results)
        
        print(f"\n📊 Batch Summary: {successful}/{len(pdfs)} successful")
        print(f"⏱️ Total time: {total_time:.2f}s")
        
        return successful > 0
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return False


if __name__ == "__main__":
    # Run main test
    main_success = test_end_to_end_pipeline()
    
    # Run batch test if main test passed
    if main_success:
        batch_success = test_batch_processing()
    else:
        batch_success = False
    
    # Final result
    if main_success and batch_success:
        print("\n🎉 ALL TESTS PASSED - Pipeline is fully functional!")
        exit(0)
    elif main_success:
        print("\n✅ Core pipeline working - batch processing needs work")
        exit(0)
    else:
        print("\n❌ Pipeline needs fixes before deployment")
        exit(1)