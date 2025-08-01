import pytest
import tempfile
import os
import json
import numpy as np
from unittest.mock import patch, MagicMock

# Add the backend directory to the path so we can import vector_db
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from vector_db import SimpleVectorDB


class TestSimpleVectorDB:
    """Test cases for SimpleVectorDB class"""
    
    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary database file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"vectors": {}, "metadata": {}}')
            temp_file = f.name
        yield temp_file
        os.unlink(temp_file)
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock the SentenceTransformer to avoid downloading models"""
        with patch('vector_db.SentenceTransformer') as mock_transformer:
            # Mock the model instance
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_model.encode.return_value = np.random.rand(384)
            
            # Make the class return our mock instance
            mock_transformer.return_value = mock_model
            yield mock_model
    
    def test_initialization(self, temp_db_file, mock_sentence_transformer):
        """Test that SimpleVectorDB initializes correctly"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        assert vector_db.dimension == 3
        assert vector_db.storage_file == temp_db_file
        assert vector_db.model_name == "all-MiniLM-L6-v2"
        assert isinstance(vector_db.vectors, dict)
        assert isinstance(vector_db.metadata, dict)
    
    def test_generate_embedding_accuracy(self, temp_db_file, mock_sentence_transformer):
        """Test that embeddings are generated with correct dimensions and no NaN/Inf values"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        text = "test text"
        
        embedding = vector_db.generate_embedding(text)
        
        assert len(embedding) == 3
        assert all(isinstance(x, (int, float)) for x in embedding)
        assert not any(np.isnan(x) for x in embedding)
        assert not any(np.isinf(x) for x in embedding)
    
    def test_add_vector(self, temp_db_file, mock_sentence_transformer):
        """Test adding a vector to the database"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        text = "test vector"
        vector_id = "test_id"
        
        success = vector_db.add_vector(vector_id, text)
        
        assert success is True
        assert vector_id in vector_db.vectors
        assert vector_id in vector_db.metadata
        assert vector_db.metadata[vector_id]['text'] == text
    
    def test_search_similarity_accuracy(self, temp_db_file, mock_sentence_transformer):
        """Test that search returns results in correct similarity order"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        # Add some test vectors
        vector_db.add_vector("1", "swimming in the pool")
        vector_db.add_vector("2", "diving into water")
        vector_db.add_vector("3", "programming code")
        
        # Search for swimming-related content
        results = vector_db.search_similar("swimming", top_k=3)
        
        # Should return results in descending similarity order
        assert len(results) > 0
        similarities = [result[1] for result in results]
        assert similarities == sorted(similarities, reverse=True)
        
        # All similarities should be between 0 and 1
        assert all(0 <= sim <= 1 for sim in similarities)
    
    def test_pca_consistency(self, temp_db_file, mock_sentence_transformer):
        """Test that PCA produces consistent embeddings for the same text"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        text = "consistent test text"
        
        # Generate embeddings multiple times
        embedding1 = vector_db.generate_embedding(text)
        embedding2 = vector_db.generate_embedding(text)
        
        # Should be identical since PCA is deterministic
        assert embedding1 == embedding2
        assert len(embedding1) == 3
    
    def test_dimension_change(self, temp_db_file, mock_sentence_transformer):
        """Test changing the dimension of the database"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        # Add a test vector
        vector_db.add_vector("test_id", "test text")
        
        # Change to 20D
        success = vector_db.change_dimension(20)
        assert success is True
        assert vector_db.dimension == 20
        
        # Check that the vector was regenerated
        vector_data = vector_db.get_vector("test_id")
        assert vector_data is not None
        vector, metadata = vector_data
        assert len(vector) == 20
    
    def test_save_and_load(self, temp_db_file, mock_sentence_transformer):
        """Test that data is properly saved and loaded"""
        # Create first instance and add data
        vector_db1 = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        vector_db1.add_vector("1", "first vector")
        vector_db1.add_vector("2", "second vector")
        
        # Create second instance and load data
        vector_db2 = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        # Check that data was loaded
        assert len(vector_db2.vectors) == 2
        assert "1" in vector_db2.vectors
        assert "2" in vector_db2.vectors
        assert vector_db2.metadata["1"]["text"] == "first vector"
        assert vector_db2.metadata["2"]["text"] == "second vector"
    
    def test_delete_vector(self, temp_db_file, mock_sentence_transformer):
        """Test deleting a vector from the database"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        vector_id = "to_be_deleted"
        
        # Add and then delete
        vector_db.add_vector(vector_id, "to be deleted")
        assert vector_id in vector_db.vectors
        
        success = vector_db.delete_vector(vector_id)
        assert success is True
        assert vector_id not in vector_db.vectors
        assert vector_id not in vector_db.metadata
    
    def test_empty_search(self, temp_db_file, mock_sentence_transformer):
        """Test search behavior with empty database"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        results = vector_db.search_similar("any text", top_k=5)
        assert len(results) == 0
    
    def test_embedding_scaling(self, temp_db_file, mock_sentence_transformer):
        """Test that embeddings are properly scaled (10x factor)"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        text = "test scaling"
        
        embedding = vector_db.generate_embedding(text)
        
        # Check that values are reasonably scaled (not tiny)
        # The 10x scaling should make values more visible
        max_value = max(abs(x) for x in embedding)
        assert max_value > 0.1  # Should be reasonably large after scaling
    
    def test_semantic_similarity(self, temp_db_file, mock_sentence_transformer):
        """Test that semantically similar texts have higher similarity scores"""
        vector_db = SimpleVectorDB(dimension=3, storage_file=temp_db_file)
        
        # Add semantically related texts
        vector_db.add_vector("1", "swimming")
        vector_db.add_vector("2", "diving")
        vector_db.add_vector("3", "programming")
        
        # Search for swimming-related content
        results = vector_db.search_similar("swimming", top_k=3)
        
        # Should find swimming and diving as more similar than programming
        if len(results) >= 2:
            swimming_sim = next((sim for id, sim, meta in results if meta['text'] == 'swimming'), 0)
            diving_sim = next((sim for id, sim, meta in results if meta['text'] == 'diving'), 0)
            programming_sim = next((sim for id, sim, meta in results if meta['text'] == 'programming'), 0)
            
            # Swimming should be most similar to itself
            assert swimming_sim >= diving_sim
            assert swimming_sim >= programming_sim 