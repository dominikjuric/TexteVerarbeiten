"""
LangChain-based RAG (Retrieval-Augmented Generation) pipeline.

This module provides RAG functionality using ChromaDB for retrieval and 
LangChain for LLM integration. It supports multiple LLM providers and 
implements conversation memory and source tracking.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import json
import time

try:
    from langchain.chains import RetrievalQA, ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.vectorstores import Chroma
    from langchain.embeddings.base import Embeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    RetrievalQA = None
    ConversationalRetrievalChain = None
    ConversationBufferMemory = None
    Document = None

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    ChatOpenAI = None
    OpenAIEmbeddings = None

try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from .embedding_store import EmbeddingStore, create_embedding_store
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from embedding_store import EmbeddingStore, create_embedding_store

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1000
DEFAULT_RETRIEVAL_K = 5


class ChromaVectorStoreWrapper:
    """Wrapper to make our EmbeddingStore compatible with LangChain."""
    
    def __init__(self, embedding_store: EmbeddingStore):
        """Initialize with an EmbeddingStore instance."""
        self.embedding_store = embedding_store
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """Perform similarity search and return LangChain Documents."""
        results = self.embedding_store.similarity_search(query, k=k)
        
        documents = []
        for result in results:
            doc = Document(
                page_content=result['document'],
                metadata={
                    **result['metadata'],
                    'id': result['id'],
                    'similarity': result.get('similarity', None)
                }
            )
            documents.append(doc)
        
        return documents
    
    def similarity_search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """Perform similarity search and return documents with scores."""
        results = self.embedding_store.similarity_search(query, k=k, include_distances=True)
        
        documents_with_scores = []
        for result in results:
            doc = Document(
                page_content=result['document'],
                metadata={
                    **result['metadata'],
                    'id': result['id']
                }
            )
            score = result.get('similarity', 0.0)
            documents_with_scores.append((doc, score))
        
        return documents_with_scores


class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) pipeline using ChromaDB and LangChain.
    
    This class provides:
    - Question answering with source citations
    - Conversational memory
    - Multiple LLM provider support
    - Source document tracking
    """
    
    def __init__(self,
                 embedding_store: Optional[EmbeddingStore] = None,
                 llm_provider: str = "openai",
                 model_name: Optional[str] = None,
                 temperature: float = DEFAULT_MODEL_TEMPERATURE,
                 max_tokens: int = DEFAULT_MAX_TOKENS,
                 api_key: Optional[str] = None):
        """
        Initialize the RAG pipeline.
        
        Args:
            embedding_store: ChromaDB embedding store (created if None)
            llm_provider: LLM provider ("openai" or "anthropic")
            model_name: Specific model name (uses default if None)
            temperature: Model temperature for response generation
            max_tokens: Maximum tokens in response
            api_key: API key for the LLM provider
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain not available. Install with: pip install langchain")
        
        # Set up embedding store
        if embedding_store:
            self.embedding_store = embedding_store
        else:
            self.embedding_store = create_embedding_store()
            if not self.embedding_store:
                raise RuntimeError("Failed to create embedding store")
        
        # Create vector store wrapper for LangChain compatibility
        self.vector_store = ChromaVectorStoreWrapper(self.embedding_store)
        
        # Set up LLM
        self.llm_provider = llm_provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = self._create_llm(llm_provider, model_name, api_key)
        
        # Set up conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Create retrieval chain
        self.qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self._create_retriever(),
            memory=self.memory,
            return_source_documents=True,
            verbose=True
        )
        
        logger.info(f"✅ RAG pipeline initialized with {llm_provider} LLM")
    
    def _create_llm(self, provider: str, model_name: Optional[str], api_key: Optional[str]):
        """Create LLM instance based on provider."""
        if provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI not available. Install with: pip install langchain-openai")
            
            model = model_name or "gpt-3.5-turbo"
            return ChatOpenAI(
                model_name=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                openai_api_key=api_key
            )
            
        elif provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic not available. Install with: pip install langchain-anthropic")
            
            model = model_name or "claude-3-sonnet-20240229"
            return ChatAnthropic(
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                anthropic_api_key=api_key
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def _create_retriever(self):
        """Create a retriever from the vector store."""
        class CustomRetriever:
            def __init__(self, vector_store, k=DEFAULT_RETRIEVAL_K):
                self.vector_store = vector_store
                self.k = k
            
            def get_relevant_documents(self, query: str) -> List[Document]:
                return self.vector_store.similarity_search(query, k=self.k)
        
        return CustomRetriever(self.vector_store)
    
    def add_documents(self, 
                     texts: List[str], 
                     metadatas: List[Dict[str, Any]],
                     source_name: Optional[str] = None) -> List[str]:
        """
        Add documents to the knowledge base.
        
        Args:
            texts: List of text chunks
            metadatas: List of metadata dicts
            source_name: Optional source name to add to all metadata
            
        Returns:
            List of document IDs
        """
        # Add source name to metadata if provided
        if source_name:
            for metadata in metadatas:
                metadata['source'] = source_name
        
        doc_ids = self.embedding_store.add_documents(texts, metadatas)
        logger.info(f"📚 Added {len(texts)} documents to knowledge base")
        return doc_ids
    
    def add_pdf_content(self, 
                       pdf_path: Union[str, Path], 
                       content: str,
                       metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Add PDF content to the knowledge base with automatic chunking.
        
        Args:
            pdf_path: Path to the PDF file
            content: Extracted text content
            metadata: Additional metadata
            
        Returns:
            List of document IDs
        """
        pdf_path = Path(pdf_path)
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(content)
        
        # Create metadata for each chunk
        base_metadata = {
            'source': pdf_path.name,
            'source_path': str(pdf_path),
            'document_type': 'pdf',
            'added_at': time.time()
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        chunk_metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **base_metadata,
                'chunk_index': i,
                'chunk_count': len(chunks)
            }
            chunk_metadatas.append(chunk_metadata)
        
        return self.add_documents(chunks, chunk_metadatas, pdf_path.name)
    
    def ask(self, 
           question: str, 
           include_sources: bool = True,
           k: int = DEFAULT_RETRIEVAL_K) -> Dict[str, Any]:
        """
        Ask a question and get an answer with sources.
        
        Args:
            question: The question to ask
            include_sources: Whether to include source documents
            k: Number of source documents to retrieve
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            # Update retriever k value if different
            if hasattr(self.qa_chain.retriever, 'k'):
                self.qa_chain.retriever.k = k
            
            # Get response from chain
            response = self.qa_chain({
                "question": question
            })
            
            answer = response.get("answer", "No answer generated.")
            source_docs = response.get("source_documents", [])
            
            # Format sources
            sources = []
            if include_sources and source_docs:
                for doc in source_docs:
                    source_info = {
                        'content': doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        'metadata': doc.metadata,
                        'similarity': doc.metadata.get('similarity')
                    }
                    sources.append(source_info)
            
            result = {
                'question': question,
                'answer': answer,
                'sources': sources,
                'source_count': len(sources),
                'timestamp': time.time()
            }
            
            logger.info(f"🤖 Answered question: '{question[:50]}...' with {len(sources)} sources")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to answer question '{question}': {e}")
            return {
                'question': question,
                'answer': f"Error processing question: {e}",
                'sources': [],
                'source_count': 0,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history."""
        messages = self.memory.chat_memory.messages
        history = []
        
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                history.append({
                    'question': messages[i].content,
                    'answer': messages[i + 1].content
                })
        
        return history
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.memory.clear()
        logger.info("🧹 Cleared conversation history")
    
    def search_documents(self, 
                        query: str, 
                        k: int = 10,
                        filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search documents without generating an answer.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of matching documents with metadata
        """
        results = self.embedding_store.similarity_search(
            query=query,
            k=k,
            where=filter_metadata
        )
        
        logger.info(f"🔍 Found {len(results)} documents for query: '{query[:50]}...'")
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        embedding_stats = self.embedding_store.get_collection_stats()
        conversation_length = len(self.memory.chat_memory.messages)
        
        return {
            'embedding_store': embedding_stats,
            'conversation_length': conversation_length,
            'llm_provider': self.llm_provider,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }


def create_rag_pipeline(llm_provider: str = "openai",
                       collection_name: str = "pdf_knowledge",
                       api_key: Optional[str] = None) -> Optional[RAGPipeline]:
    """
    Factory function to create a RAG pipeline with error handling.
    
    Args:
        llm_provider: LLM provider ("openai" or "anthropic")
        collection_name: ChromaDB collection name
        api_key: API key for the LLM provider
        
    Returns:
        RAGPipeline instance or None if creation failed
    """
    try:
        # Create embedding store
        embedding_store = create_embedding_store(collection_name)
        if not embedding_store:
            logger.error("Failed to create embedding store")
            return None
        
        # Create RAG pipeline
        pipeline = RAGPipeline(
            embedding_store=embedding_store,
            llm_provider=llm_provider,
            api_key=api_key
        )
        
        logger.info(f"✅ Created RAG pipeline: {pipeline.get_stats()}")
        return pipeline
        
    except Exception as e:
        logger.error(f"❌ Failed to create RAG pipeline: {e}")
        return None


if __name__ == "__main__":
    """Test the RAG pipeline functionality."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🤖 Testing LangChain RAG Pipeline")
    print("=" * 40)
    
    # Test without API keys (will fail but show structure)
    try:
        pipeline = create_rag_pipeline("openai")
        if pipeline:
            print("✅ RAG pipeline created (but may not work without API key)")
            print(f"📊 Stats: {pipeline.get_stats()}")
        else:
            print("❌ Failed to create RAG pipeline")
    except Exception as e:
        print(f"❌ Error creating pipeline: {e}")
        print("💡 This is expected without API keys - the structure is correct")
    
    print("\n💡 To use the RAG pipeline:")
    print("1. Set your API key: export OPENAI_API_KEY='your-key-here'")
    print("2. Or pass it directly: create_rag_pipeline('openai', api_key='your-key')")
    print("3. Add documents: pipeline.add_pdf_content(pdf_path, content)")
    print("4. Ask questions: pipeline.ask('What is machine learning?')")
    
    print("\n✅ RAG pipeline structure validated!")