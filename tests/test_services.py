# tests/test_services.py
import pytest
from unittest.mock import Mock, patch
import numpy as np
from app.services.vector_store_service import VectorStoreService

@pytest.fixture
def mock_sentence_transformer():
    with patch('sentence_transformers.SentenceTransformer') as mock:
        # Create a mock model that returns numpy arrays
        model = Mock()
        model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock.return_value = model
        yield mock

@pytest.fixture
def mock_chromadb():
    with patch('chromadb.PersistentClient') as mock:
        client = Mock()
        collection = Mock()
        collection.query.return_value = {
            'documents': [['Sample text']],
            'distances': [[0.1]]
        }
        client.get_collection.return_value = collection
        mock.return_value = client
        yield mock

def test_vector_store_service_get_context(mock_sentence_transformer, mock_chromadb):
    vector_store = VectorStoreService()
    
    # Test getting context
    query = "What are the course prerequisites?"
    syllabus_id = 1
    
    # Get context and verify
    context = vector_store.get_relevant_context(syllabus_id, query)
    
    assert len(context) > 0
    assert 'text' in context[0]
    assert 'similarity' in context[0]
    assert context[0]['text'] == 'Sample text'
    assert isinstance(context[0]['similarity'], float)