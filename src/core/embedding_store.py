"""
ChromaDB-based embedding store for the PDF knowledge pipeline.

This module provides semantic search capabilities using ChromaDB as the vector database
and sentence transformers for generating embeddings. It integrates with the PDF pipeline
to store and retrieve document chunks based on semantic similarity.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import time

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast and good quality
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
CHROMA_DB_DIR = Path("processed/chroma_db")


class EmbeddingStore:
    """
    ChromaDB-based vector store for semantic document search.
    
    This class provides functionality to:
    - Store document chunks with embeddings
    - Perform semantic similarity search
    - Manage document metadata
    - Handle incremental updates
    """
    
    def __init__(self, 
                 collection_name: str = "pdf_knowledge",
                 persist_directory: Optional[Path] = None,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL,
                 embedding_function: Optional[Any] = None):
        """
        Initialize the embedding store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist ChromaDB data (default: processed/chroma_db)
            embedding_model: Sentence transformer model name
            embedding_function: Custom embedding function (overrides embedding_model)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB not available. Install with: pip install chromadb"
            )
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory or CHROMA_DB_DIR
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Set up embedding function
        if embedding_function:
            self.embedding_function = embedding_function
            self.embedding_model_name = "custom"
        else:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                # Fallback to default ChromaDB embedding
                logger.warning("Sentence Transformers not available, using default embeddings")
                self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                self.embedding_model_name = "default"
            else:
                # Use sentence transformers
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=embedding_model
                )
                self.embedding_model_name = embedding_model
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"📖 Loaded existing collection '{collection_name}' with {self.collection.count()} documents")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "PDF knowledge base embeddings"}
            )
            logger.info(f"🆕 Created new collection '{collection_name}'")
    
    def add_document(self, 
                    text: str, 
                    metadata: Dict[str, Any],
                    doc_id: Optional[str] = None) -> str:
        """
        Add a single document to the store.
        
        Args:
            text: Document text content
            metadata: Document metadata
            doc_id: Optional document ID (auto-generated if None)
            
        Returns:
            Document ID
        """
        return self.add_documents([text], [metadata], [doc_id] if doc_id else None)[0]
    
    def add_documents(self, 
                     texts: List[str], 
                     metadatas: List[Dict[str, Any]], 
                     ids: Optional[List[str]] = None) -> List[str]:
        """
        Add multiple documents to the embedding store.
        
        Args:
            texts: List of text chunks to embed
            metadatas: List of metadata dicts for each text
            ids: Optional list of unique IDs (auto-generated if None)
            
        Returns:
            List of document IDs
        """
        if not texts:
            logger.warning("No texts provided to add_documents")
            return []
        
        if len(texts) != len(metadatas):
            raise ValueError("Number of texts and metadatas must match")
        
        # Generate IDs if not provided
        if ids is None:
            ids = []
            for i, text in enumerate(texts):
                # Create deterministic ID based on content hash
                content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                timestamp = int(time.time())
                doc_id = f"doc_{timestamp}_{i}_{content_hash}"
                ids.append(doc_id)
        
        # Add to ChromaDB
        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ Added {len(texts)} documents to collection '{self.collection_name}'")
            return ids
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
            raise
    
    def similarity_search(self, 
                         query: str, 
                         k: int = 5,
                         where: Optional[Dict[str, Any]] = None,
                         where_document: Optional[Dict[str, Any]] = None,
                         include_distances: bool = True) -> List[Dict[str, Any]]:
        """
        Perform similarity search.
        
        Args:
            query: Search query text
            k: Number of results to return
            where: Optional metadata filter
            where_document: Optional document content filter
            include_distances: Whether to include similarity distances
            
        Returns:
            List of search results with documents, metadata, and optionally distances
        """
        try:
            # Prepare include list
            include = ["documents", "metadatas"]
            if include_distances:
                include.append("distances")
            
            # Search ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=where,
                where_document=where_document,
                include=include
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'id': results['ids'][0][i]
                    }
                    
                    if include_distances and 'distances' in results:
                        result['distance'] = results['distances'][0][i]
                        result['similarity'] = 1 - results['distances'][0][i]  # Convert distance to similarity
                    
                    formatted_results.append(result)
            
            logger.info(f"🔍 Found {len(formatted_results)} results for query: '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve documents by their IDs.
        
        Args:
            ids: List of document IDs
            
        Returns:
            List of documents with metadata
        """
        try:
            results = self.collection.get(
                ids=ids,
                include=["documents", "metadatas"]
            )
            
            formatted_results = []
            if results['documents']:
                for i, doc_id in enumerate(results['ids']):
                    formatted_results.append({
                        'id': doc_id,
                        'document': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Failed to get documents by IDs: {e}")
            return []
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents by their IDs.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            True if successful
        """
        try:
            self.collection.delete(ids=ids)
            logger.info(f"🗑️ Deleted {len(ids)} documents")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete documents: {e}")
            return False
    
    def delete_by_metadata(self, where: Dict[str, Any]) -> bool:
        """
        Delete documents by metadata filter.
        
        Args:
            where: Metadata filter
            
        Returns:
            True if successful
        """
        try:
            self.collection.delete(where=where)
            logger.info(f"🗑️ Deleted documents matching filter: {where}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete documents by metadata: {e}")
            return False
    
    def update_document(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Update a document's content and metadata.
        
        Args:
            doc_id: Document ID
            text: New text content
            metadata: New metadata
            
        Returns:
            True if successful
        """
        try:
            self.collection.update(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata]
            )
            logger.info(f"📝 Updated document {doc_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update document {doc_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        count = self.collection.count()
        return {
            'collection_name': self.collection_name,
            'document_count': count,
            'embedding_model': self.embedding_model_name,
            'persist_directory': str(self.persist_directory)
        }
    
    def reset_collection(self) -> bool:
        """
        Reset (clear) the entire collection.
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "PDF knowledge base embeddings"}
            )
            logger.info(f"🔄 Reset collection '{self.collection_name}'")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reset collection: {e}")
            return False


def chunk_text(text: str, 
               chunk_size: int = DEFAULT_CHUNK_SIZE, 
               chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to split
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Number of overlapping characters
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending within the last 100 characters
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = max(start + 1, end - chunk_overlap)
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks


def create_embedding_store(collection_name: str = "pdf_knowledge",
                          embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> Optional[EmbeddingStore]:
    """
    Factory function to create an embedding store with error handling.
    
    Args:
        collection_name: Name of the ChromaDB collection
        embedding_model: Sentence transformer model name
        
    Returns:
        EmbeddingStore instance or None if creation failed
    """
    try:
        store = EmbeddingStore(
            collection_name=collection_name,
            embedding_model=embedding_model
        )
        logger.info(f"✅ Created embedding store: {store.get_collection_stats()}")
        return store
    except ImportError as e:
        logger.error(f"❌ Cannot create embedding store - missing dependencies: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to create embedding store: {e}")
        return None


if __name__ == "__main__":
    """Test the embedding store functionality."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🧠 Testing ChromaDB Embedding Store")
    print("=" * 40)
    
    # Test store creation
    store = create_embedding_store("test_collection")
    if not store:
        print("❌ Failed to create embedding store")
        exit(1)
    
    print(f"✅ Created store: {store.get_collection_stats()}")
    
    # Test adding documents
    test_documents = [
        "Machine learning is a subset of artificial intelligence that focuses on algorithms.",
        "Deep learning uses neural networks with multiple layers to process data.",
        "Natural language processing helps computers understand human language.",
        "Computer vision enables machines to interpret visual information.",
        "Reinforcement learning trains agents through reward-based interactions."
    ]
    
    test_metadata = [
        {"topic": "ML", "source": "test", "category": "definition"},
        {"topic": "DL", "source": "test", "category": "definition"},
        {"topic": "NLP", "source": "test", "category": "definition"},
        {"topic": "CV", "source": "test", "category": "definition"},
        {"topic": "RL", "source": "test", "category": "definition"}
    ]
    
    print(f"\n💾 Adding {len(test_documents)} test documents...")
    doc_ids = store.add_documents(test_documents, test_metadata)
    print(f"✅ Added documents with IDs: {doc_ids}")
    
    # Test similarity search
    print(f"\n🔍 Testing similarity search...")
    query = "What is artificial intelligence?"
    results = store.similarity_search(query, k=3)
    
    print(f"Query: '{query}'")
    print("Results:")
    for i, result in enumerate(results):
        print(f"  {i+1}. (similarity: {result.get('similarity', 'N/A'):.3f})")
        print(f"     {result['document'][:100]}...")
        print(f"     Metadata: {result['metadata']}")
    
    # Test metadata filtering
    print(f"\n🔍 Testing metadata filtering...")
    ml_results = store.similarity_search(
        "learning algorithms", 
        k=3, 
        where={"topic": "ML"}
    )
    print(f"Found {len(ml_results)} ML-specific results")
    
    # Show final stats
    final_stats = store.get_collection_stats()
    print(f"\n📊 Final collection stats: {final_stats}")
    
    print("\n✅ All tests completed successfully!")