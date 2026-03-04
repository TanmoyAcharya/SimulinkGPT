"""
Knowledge Base Manager

Handles the RAG (Retrieval-Augmented Generation) pipeline for 
Simulink domain knowledge retrieval.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class KnowledgeDocument:
    """Represents a knowledge base document."""
    
    def __init__(
        self,
        content: str,
        source: str,
        title: str = "",
        doc_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.source = source
        self.title = title or source
        self.doc_type = doc_type
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "title": self.title,
            "doc_type": self.doc_type,
            "metadata": self.metadata
        }


class KnowledgeBaseManager:
    """
    Manages the knowledge base for RAG-powered Simulink assistance.
    
    This class handles:
    - Document loading and preprocessing
    - Vector embedding generation
    - Similarity search
    - Context retrieval
    """
    
    def __init__(
        self,
        vector_store_path: str = "./knowledge_base/vector_store",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the knowledge base manager.
        
        Args:
            vector_store_path: Path to store the vector database
            embedding_model: HuggingFace model for embeddings
            chunk_size: Text chunk size for splitting documents
            chunk_overlap: Overlap between chunks
        """
        self.vector_store_path = vector_store_path
        self.embedding_model_name = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.embeddings = None
        self.vector_store = None
        self.documents = []
        
        # Initialize components
        self._init_embeddings()
        self._init_vector_store()
    
    def _init_embeddings(self):
        """Initialize the embedding model."""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'}  # Use CPU if no GPU
            )
            logger.info(f"Initialized embeddings with model: {self.embedding_model_name}")
        except ImportError:
            logger.warning("Could not load LangChain embeddings, using placeholder")
            self.embeddings = None
    
    def _init_vector_store(self):
        """Initialize the vector store (ChromaDB)."""
        try:
            import chromadb
            from langchain_community.vectorstores import Chroma
            
            # Create directory if needed
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Initialize Chroma client
            self.chroma_client = chromadb.PersistentClient(
                path=self.vector_store_path
            )
            
            self.vector_store = Chroma(
                client=self.chroma_client,
                embedding_function=self.embeddings,
                collection_name="simulink_knowledge"
            )
            
            logger.info(f"Initialized vector store at: {self.vector_store_path}")
        except ImportError:
            logger.warning("ChromaDB not available, using in-memory fallback")
            self._init_fallback_vector_store()
        except Exception as e:
            logger.warning(f"Could not initialize vector store: {e}")
            self._init_fallback_vector_store()
    
    def _init_fallback_vector_store(self):
        """Initialize a simple in-memory vector store fallback."""
        self.vector_store = None
        self.documents = []
    
    def add_document(self, doc: KnowledgeDocument) -> None:
        """Add a single document to the knowledge base."""
        self.documents.append(doc)
        
        if self.vector_store:
            try:
                self.vector_store.add_texts(
                    texts=[doc.content],
                    metadatas=[{
                        "source": doc.source,
                        "title": doc.title,
                        "doc_type": doc.doc_type,
                        **doc.metadata
                    }],
                    ids=[f"doc_{len(self.documents)}"]
                )
            except Exception as e:
                logger.error(f"Error adding document to vector store: {e}")
    
    def add_documents(self, docs: List[KnowledgeDocument]) -> None:
        """Add multiple documents to the knowledge base."""
        for doc in docs:
            self.add_document(doc)
        
        logger.info(f"Added {len(docs)} documents to knowledge base")
    
    def load_documents_from_directory(
        self,
        directory: str,
        glob_pattern: str = "**/*.md"
    ) -> int:
        """
        Load all documents from a directory.
        
        Args:
            directory: Path to directory containing documents
            glob_pattern: Glob pattern for file matching
            
        Returns:
            Number of documents loaded
        """
        path = Path(directory)
        if not path.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0
        
        loaded = 0
        for file_path in path.glob(glob_pattern):
            try:
                content = file_path.read_text(encoding='utf-8')
                doc = KnowledgeDocument(
                    content=content,
                    source=str(file_path),
                    title=file_path.stem,
                    doc_type=self._get_doc_type_from_extension(file_path.suffix)
                )
                self.add_document(doc)
                loaded += 1
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        
        logger.info(f"Loaded {loaded} documents from {directory}")
        return loaded
    
    def _get_doc_type_from_extension(self, ext: str) -> str:
        """Determine document type from file extension."""
        type_map = {
            '.md': 'markdown',
            '.txt': 'text',
            '.pdf': 'pdf',
            '.html': 'html',
            '.json': 'json'
        }
        return type_map.get(ext.lower(), 'general')
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: The search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant document chunks with scores
        """
        if not self.vector_store:
            # Fallback: simple keyword matching
            return self._fallback_retrieve(query, top_k)
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k
            )
            
            retrieved = []
            for doc, score in results:
                # Convert score to similarity (lower is better in Chroma)
                similarity = 1.0 / (1.0 + score)
                
                if similarity >= similarity_threshold:
                    retrieved.append({
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "title": doc.metadata.get("title", "Untitled"),
                        "doc_type": doc.metadata.get("doc_type", "general"),
                        "similarity": similarity
                    })
            
            return retrieved
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return self._fallback_retrieve(query, top_k)
    
    def _fallback_retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Simple keyword-based retrieval fallback."""
        if not self.documents:
            return []
        
        query_words = set(query.lower().split())
        results = []
        
        for doc in self.documents:
            doc_words = set(doc.content.lower().split())
            # Simple Jaccard similarity
            if query_words:
                similarity = len(query_words & doc_words) / len(query_words)
                if similarity > 0:
                    results.append({
                        "content": doc.content[:500],  # Limit content
                        "source": doc.source,
                        "title": doc.title,
                        "doc_type": doc.doc_type,
                        "similarity": similarity
                    })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def build_context_from_retrieval(
        self,
        query: str,
        top_k: int = 5,
        max_context_length: int = 2000
    ) -> str:
        """
        Build a context string from retrieved documents.
        
        Args:
            query: The user's query
            top_k: Number of documents to retrieve
            max_context_length: Maximum length of context string
            
        Returns:
            Formatted context string for LLM
        """
        retrieved = self.retrieve(query, top_k=top_k)
        
        if not retrieved:
            return "No relevant knowledge base documents found."
        
        context_parts = ["=== Relevant Simulink Knowledge ===\n"]
        
        for i, doc in enumerate(retrieved, 1):
            context_parts.append(f"\n--- Document {i} (Source: {doc['source']}) ---")
            context_parts.append(doc['content'][:max_context_length // len(retrieved)])
        
        return "\n".join(context_parts)
    
    def save(self) -> None:
        """Persist the knowledge base to disk."""
        # Save documents as JSON
        docs_path = os.path.join(self.vector_store_path, "documents.json")
        
        docs_data = [doc.to_dict() for doc in self.documents]
        
        with open(docs_path, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f, indent=2)
        
        logger.info(f"Saved {len(self.documents)} documents to {docs_path}")
    
    def load(self) -> int:
        """Load the knowledge base from disk."""
        docs_path = os.path.join(self.vector_store_path, "documents.json")
        
        if not os.path.exists(docs_path):
            return 0
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        
        for doc_data in docs_data:
            doc = KnowledgeDocument(
                content=doc_data["content"],
                source=doc_data["source"],
                title=doc_data["title"],
                doc_type=doc_data["doc_type"],
                metadata=doc_data.get("metadata", {})
            )
            self.add_document(doc)
        
        logger.info(f"Loaded {len(self.documents)} documents from {docs_path}")
        return len(self.documents)
