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

    def get_full_syllabus_content(self, syllabus_id: int) -> str:
        """Get the full content of the syllabus from ChromaDB."""
        try:
            collection_name = f"syllabus_{syllabus_id}"
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Get all documents
            results = collection.get()
            
            if results and 'documents' in results:
                # Combine all chunks into one text
                full_text = " ".join(results['documents'])
                return full_text
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting full syllabus content: {str(e)}")
            return ""

    def get_relevant_context(self, syllabus_id: int, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Get relevant context by using the full syllabus content."""
        try:
            # Get full syllabus content
            full_content = self.get_full_syllabus_content(syllabus_id)
            
            if not full_content:
                logger.warning(f"No content found for syllabus {syllabus_id}")
                return []
            
            # Create a context with the full content
            return [{
                'text': full_content,
                'similarity': 1.0
            }]
            
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []