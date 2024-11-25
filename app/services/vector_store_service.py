# app/services/vector_store_service.py
from typing import List, Dict, Any
import chromadb
from flask import current_app
import logging
import os
import tempfile
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        # Create a temporary directory for ChromaDB
        self.persist_dir = os.path.join(tempfile.gettempdir(), "chroma_db")
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize ChromaDB with new client format
        self.chroma_client = chromadb.PersistentClient(
            path=self.persist_dir
        )
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        
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
            
            # Generate embedding for the query
            query_embedding = self._generate_embedding(query)
            
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
                        'similarity': 1 - float(results['distances'][0][i])  # Convert distance to similarity
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        try:
            embedding = self.model.encode([text], convert_to_numpy=True)[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise