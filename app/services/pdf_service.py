# app/services/pdf_service.py
import PyPDF2
import os
import logging
from werkzeug.utils import secure_filename
from flask import current_app
from typing import List, Generator
import chromadb
import tempfile
from sentence_transformers import SentenceTransformer
import numpy as np
import traceback
from chromadb.errors import InvalidCollectionException
import gc

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        try:
            self.persist_dir = os.path.join(tempfile.gettempdir(), "chroma_db")
            os.makedirs(self.persist_dir, exist_ok=True)
            
            logger.info(f"Initializing ChromaDB with persist_dir: {self.persist_dir}")
            
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_dir
            )
            
            logger.info("ChromaDB client initialized successfully")
            
            # Initialize the sentence transformer model
            logger.info("Loading sentence transformer model")
            self.model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing PDFProcessor: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file."""
        try:
            logger.info(f"Attempting to extract text from PDF: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found at path: {file_path}")
            
            with open(file_path, 'rb') as file:
                # Create PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)
                text = []
                
                # Extract text from each page
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        text.append(page.extract_text())
                        logger.debug(f"Successfully extracted text from page {page_num + 1}")
                    except Exception as e:
                        logger.error(f"Error on page {page_num + 1}: {str(e)}")
                
                # Combine all text with proper spacing
                full_text = " ".join(text)
                
                # Basic text cleaning
                full_text = " ".join(full_text.split())  # Remove extra whitespace
                full_text = full_text.replace('\x00', '')  # Remove null bytes
                
                if not full_text.strip():
                    raise ValueError("No text content extracted from PDF")
                
                # Log a preview of the extracted text
                logger.info(f"Text preview (first 200 chars): {full_text[:200]}")
                return full_text
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise


    def verify_collection(self, collection_name: str) -> bool:
        """Verify that a collection exists and contains data."""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            count = collection.count()
            logger.info(f"Collection {collection_name} exists with {count} items")
            return count > 0
        except Exception as e:
            logger.error(f"Error verifying collection {collection_name}: {str(e)}")
            return False
        
    def create_text_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
            """Split text into overlapping chunks."""
            try:
                logger.info(f"Chunking text of length {len(text)} with chunk_size={chunk_size}, overlap={overlap}")
                
                if not text:
                    raise ValueError("Input text is empty")
                
                chunks = []
                start = 0
                text_length = len(text)

                while start < text_length:
                    end = min(start + chunk_size, text_length)
                    
                    # Find the last period or newline in the chunk
                    chunk = text[start:end]
                    last_period_pos = max(
                        chunk.rfind('. '),
                        chunk.rfind('\n')
                    )
                    
                    if last_period_pos != -1:
                        # Adjust end position to include the period
                        end = start + last_period_pos + 2
                    
                    # Get the chunk and clean it
                    current_chunk = text[start:end].strip()
                    
                    if current_chunk:  # Only add non-empty chunks
                        chunks.append(current_chunk)
                    
                    # Move the start position, considering overlap
                    start = max(end - overlap, start + 1)  # Ensure we make progress
                    
                    # Free up memory
                    del chunk
                    gc.collect()
                    
                logger.info(f"Created {len(chunks)} chunks")
                return chunks

            except Exception as e:
                logger.error(f"Error chunking text: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise

    def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers with memory optimization."""
        try:
            if not chunks:
                raise ValueError("No chunks provided for embedding generation")
            
            logger.info(f"Generating embeddings for chunks")
            
            # Use smaller batch size to manage memory
            batch_size = 4  # Reduced from 8 to 4
            embeddings = []
            
            # Process in smaller batches with garbage collection
            import gc
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
                
                # Generate embeddings for batch
                batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                embeddings.extend(batch_embeddings.tolist())
                
                # Clean up memory
                del batch_embeddings
                del batch
                gc.collect()
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def store_vectors(self, syllabus_id: int, chunks: List[str], embeddings: List[List[float]]) -> str:
        """Store text chunks and their embeddings in ChromaDB."""
        try:
            if not chunks or not embeddings:
                raise ValueError("Empty chunks or embeddings provided")
                
            collection_name = f"syllabus_{syllabus_id}"
            logger.info(f"Storing vectors for collection: {collection_name}")
            
            # Clean and verify chunks
            cleaned_chunks = []
            for chunk in chunks:
                # Basic cleaning
                cleaned_chunk = chunk.strip()
                cleaned_chunk = " ".join(cleaned_chunk.split())  # Normalize whitespace
                
                if cleaned_chunk and not cleaned_chunk.endswith('.pdf'):  # Verify it's not just a file path
                    cleaned_chunks.append(cleaned_chunk)
                else:
                    logger.warning(f"Skipping invalid chunk: {chunk}")
            
            if not cleaned_chunks:
                raise ValueError("No valid chunks after cleaning")
            
            # Get or create collection
            try:
                # Delete existing collection if it exists
                try:
                    self.chroma_client.delete_collection(name=collection_name)
                    logger.info(f"Deleted existing collection: {collection_name}")
                except ValueError:
                    pass
                
                # Create new collection
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")
            except Exception as e:
                logger.error(f"Error creating collection: {str(e)}")
                raise
            
            # Store in batches
            batch_size = 50
            for i in range(0, len(cleaned_chunks), batch_size):
                end_idx = min(i + batch_size, len(cleaned_chunks))
                batch_chunks = cleaned_chunks[i:end_idx]
                batch_embeddings = embeddings[i:end_idx]
                batch_ids = [f"chunk_{j}" for j in range(i, end_idx)]
                
                # Log the first chunk of each batch
                logger.info(f"Sample chunk from batch {i//batch_size}: {batch_chunks[0][:100]}...")
                
                collection.add(
                    embeddings=batch_embeddings,
                    documents=batch_chunks,
                    ids=batch_ids
                )
            
            # Verify storage
            sample_result = collection.peek()
            logger.info(f"Storage verification - sample documents: {sample_result}")
            
            return collection_name
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            raise

def process_pdf(syllabus) -> None:
    """Main function to process PDF and generate embeddings."""
    try:
        processor = PDFProcessor()
        
        # Get full file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], syllabus.file_path)
        
        # Extract text
        text = processor.extract_text_from_pdf(file_path)
        logger.info(f"Extracted text length: {len(text)}")
        
        # Create chunks and convert generator to list
        chunks = list(processor.create_text_chunks(text))
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings
        embeddings = processor.generate_embeddings(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Store vectors
        collection_name = processor.store_vectors(syllabus.id, chunks, embeddings)
        
        # Update syllabus record
        syllabus.vector_store_id = collection_name
        
    except Exception as e:
        logger.error(f"Error processing syllabus: {str(e)}")
        raise