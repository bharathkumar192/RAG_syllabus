# app/services/vector_store_service.py
import logging
import os
import tempfile
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import traceback

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        # Create a temporary directory for ChromaDB
        self.persist_dir = os.path.join(tempfile.gettempdir(), "chroma_db")
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_dir
        )
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        try:
            # Generate embedding and convert to list
            embedding = self.model.encode(text, convert_to_numpy=True)
            if isinstance(embedding, np.ndarray):
                return embedding.tolist()
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def get_relevant_context(self, syllabus_id: int, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a given query."""
        try:
            collection_name = f"syllabus_{syllabus_id}"
            
            # Get collection
            try:
                collection = self.chroma_client.get_collection(name=collection_name)
            except ValueError as e:
                logger.error(f"Collection not found: {str(e)}")
                return []
            
            # Generate embedding for the query and ensure it's a list
            query_embedding = self._generate_embedding(query)
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.tolist()
            
            # Search for similar chunks
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=num_results,
                include=["documents", "distances"]
            )
            
            # Format results
            context = []
            if results['documents']:
                for i in range(len(results['documents'][0])):
                    context.append({
                        'text': results['documents'][0][i],
                        'similarity': 1 - float(results['distances'][0][i])
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise