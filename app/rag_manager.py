import logging
import re
import os
import numpy as np
import ssl
import urllib3
import requests

# Bypass SSL verification for internal network / testing
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests to disable SSL verification globally
old_request = requests.Session.request
def new_request(self, method, url, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, **kwargs)
requests.Session.request = new_request

import numpy as np
from threading import Lock
from typing import Dict, List, Any

# Ensure we use torch if it's available, otherwise fallback is managed by sentence_transformers
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class RAGManager:
    """
    Singleton Manager for Retrieval-Augmented Generation (RAG).
    Handles text chunking, embedding generation, and semantic search.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RAGManager, cls).__new__(cls)
                cls._instance.model = None
                cls._instance.is_loaded = False
        return cls._instance

    def load_model(self):
        """Loads the sentence transformer model."""
        if self.is_loaded:
            return
            
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not installed. Add it to requirements.txt")

        logger.info("Loading RAG Embedding Model (paraphrase-multilingual-MiniLM-L12-v2)...")
        try:
            # Using multilingual model for Arabic support
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.is_loaded = True
            logger.info("RAG Embedding Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load RAG Embedding Model: {e}")
            raise

    def chunk_text(self, text: str, max_words_per_chunk: int = 200) -> List[str]:
        """
        Splits text into meaningful chunks. 
        First splits by double newlines (paragraphs), then by words if too long.
        """
        paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        chunks = []
        
        current_chunk = []
        current_word_count = 0
        
        for p in paragraphs:
            words = p.split()
            if current_word_count + len(words) <= max_words_per_chunk:
                current_chunk.append(p)
                current_word_count += len(words)
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_word_count = len(words)
                
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    def build_index(self, text: str) -> Dict[str, Any]:
        """
        Chunks the text, calculates embeddings, and returns the index data.
        """
        if not self.is_loaded:
            self.load_model()
            
        logger.info("Building RAG index...")
        chunks = self.chunk_text(text)
        
        if not chunks:
            return {"chunks": [], "embeddings": np.array([])}
            
        # Generate embeddings (returns a numpy array or torch tensor, depending on setup)
        embeddings = self.model.encode(chunks, convert_to_numpy=True)
        
        logger.info(f"RAG index built with {len(chunks)} chunks.")
        
        return {
            "chunks": chunks,
            "embeddings": embeddings
        }

    def search(self, query: str, index: Dict[str, Any], top_k: int = 3) -> List[str]:
        """
        Searches the index for the most relevant chunks using cosine similarity.
        """
        if not self.is_loaded:
            self.load_model()
            
        chunks = index.get("chunks", [])
        embeddings = index.get("embeddings", np.array([]))
        
        if not chunks or len(embeddings) == 0:
            return []
            
        # Encode the query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Calculate cosine similarity: dot product of normalized vectors
        # SentenceTransformers usually outputs normalized vectors, but we'll normalize to be safe
        query_norm = np.linalg.norm(query_embedding)
        doc_norms = np.linalg.norm(embeddings, axis=1)
        
        # Avoid division by zero
        if query_norm == 0:
            return []
            
        doc_norms[doc_norms == 0] = 1e-10
        
        similarities = np.dot(embeddings, query_embedding) / (doc_norms * query_norm)
        
        # Get top K indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = [chunks[i] for i in top_indices if similarities[i] > 0.4] # threshold for strong match
        
        return results
