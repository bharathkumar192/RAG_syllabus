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
        """Extract text content from a PDF file using a generator to manage memory."""
        try:
            logger.info(f"Attempting to extract text from PDF: {file_path}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found at path: {file_path}")
            
            # Use a generator to read pages one at a time
            def text_generator():
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text.strip():
                                yield page_text
                            logger.debug(f"Successfully extracted text from page {page_num + 1}")
                        except Exception as page_error:
                            logger.error(f"Error extracting text from page {page_num + 1}: {str(page_error)}")
            
            # Join pages with explicit memory management
            text = ""
            for page_text in text_generator():
                text += page_text
                
            if not text.strip():
                raise ValueError("No text content extracted from PDF")
                
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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
        
    def create_text_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> Generator[str, None, None]:
        """Split text into overlapping chunks with improved memory management."""
        try:
            logger.info(f"Chunking text of length {len(text)} with chunk_size={chunk_size}, overlap={overlap}")
            
            if not text:
                raise ValueError("Input text is empty")
            
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
                
                if current_chunk:  # Only yield non-empty chunks
                    yield current_chunk
                
                # Move the start position, considering overlap
                start = max(end - overlap, start + 1)  # Ensure we make progress
                
                # Free up memory
                del chunk
                import gc
                gc.collect()

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
        """Store text chunks and their embeddings in ChromaDB with memory optimization."""
        try:
            if not syllabus_id:
                raise ValueError("syllabus_id is required")
            
            collection_name = f"syllabus_{syllabus_id}"
            logger.info(f"Storing vectors for collection: {collection_name}")
            
            # Create new collection or get existing one
            try:
                # Try to delete existing collection if it exists
                try:
                    self.chroma_client.delete_collection(name=collection_name)
                    logger.info(f"Deleted existing collection: {collection_name}")
                except Exception:
                    logger.info(f"No existing collection found: {collection_name}")
                
                # Create new collection
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")
                
            except Exception as e:
                logger.error(f"Error creating collection: {str(e)}")
                raise
            
            # Store in smaller batches to manage memory
            batch_size = 25  # Reduced from 50 to 25
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            
            for i in range(0, len(chunks), batch_size):
                end_idx = min(i + batch_size, len(chunks))
                batch_chunks = chunks[i:end_idx]
                batch_embeddings = embeddings[i:end_idx]
                batch_ids = [f"chunk_{j}" for j in range(i, end_idx)]
                
                try:
                    collection.add(
                        embeddings=batch_embeddings,
                        documents=batch_chunks,
                        ids=batch_ids
                    )
                    
                    # Clean up batch data
                    del batch_chunks
                    del batch_embeddings
                    gc.collect()
                    
                    logger.debug(f"Stored batch {i//batch_size + 1}/{total_batches}")
                    
                except Exception as e:
                    logger.error(f"Error adding batch {i//batch_size + 1}: {str(e)}")
                    raise
            
            logger.info(f"Successfully stored all chunks in collection {collection_name}")
            return collection_name
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

def process_pdf(syllabus) -> None:
    """Main function to process PDF and generate embeddings."""
    try:
        if syllabus is None:
            raise ValueError("Syllabus object is required")
        
        logger.info(f"Starting PDF processing for syllabus ID: {syllabus.id}")
        
        processor = PDFProcessor()
        
        # Get the full file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], syllabus.file_path)
        logger.info(f"Processing file: {file_path}")
        
        # Extract text from PDF
        text = processor.extract_text_from_pdf(file_path)
        logger.info(f"Extracted {len(text)} characters of text")
        
        # Initialize lists to store chunks and embeddings
        all_chunks = []
        all_embeddings = []
        
        # Process chunks in batches
        chunk_generator = processor.create_text_chunks(text)
        batch_chunks = []
        batch_size = current_app.config.get('CHUNK_PROCESSING_THRESHOLD', 100)
        
        for chunk in chunk_generator:
            batch_chunks.append(chunk)
            
            # Process batch when it reaches threshold
            if len(batch_chunks) >= batch_size:
                # Generate embeddings for current batch
                batch_embeddings = processor.generate_embeddings(batch_chunks)
                
                # Store the results
                all_chunks.extend(batch_chunks)
                all_embeddings.extend(batch_embeddings)
                
                # Clear batch for next iteration
                batch_chunks = []
                
                # Log progress
                logger.info(f"Processed {len(all_chunks)} chunks so far")
        
        # Process any remaining chunks
        if batch_chunks:
            batch_embeddings = processor.generate_embeddings(batch_chunks)
            all_chunks.extend(batch_chunks)
            all_embeddings.extend(batch_embeddings)
        
        logger.info(f"Created total of {len(all_chunks)} text chunks")
        
        # Store in vector database
        collection_name = processor.store_vectors(syllabus.id, all_chunks, all_embeddings)
        
        # Verify collection was created successfully
        if not processor.verify_collection(collection_name):
            raise ValueError(f"Failed to verify collection {collection_name}")
        
        logger.info(f"Successfully verified collection: {collection_name}")
        
        # Update syllabus record with vector store ID
        syllabus.vector_store_id = collection_name
        
        logger.info(f"Successfully completed processing for syllabus ID: {syllabus.id}")
        
    except Exception as e:
        logger.error(f"Error processing syllabus {getattr(syllabus, 'id', None)}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise