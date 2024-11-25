# app/config.py
import os
from datetime import timedelta

class Config:
    # Get the base directory of the application
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Use absolute path for uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    MAX_CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 100
    EMBEDDING_BATCH_SIZE = 8
    VECTOR_STORE_BATCH_SIZE = 50
    MAX_BATCH_SIZE_EMBEDDINGS = 4
    MAX_BATCH_SIZE_STORAGE = 25
    TEXT_CHUNK_SIZE = 1000
    TEXT_CHUNK_OVERLAP = 100
    CHUNK_PROCESSING_THRESHOLD = 100
    
    # Logging configuration
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
    
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(LOG_DIR, 'syllabus_chatbot.log')
    LOG_MAX_BYTES = 10240  # 10KB
    LOG_BACKUP_COUNT = 10