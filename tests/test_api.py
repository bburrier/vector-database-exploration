import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add the backend directory to the path so we can import app
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Import app after setting up the path
from app import app

client = TestClient(app)


class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock the vector database for testing"""
        # Mock the SimpleVectorDB class itself
        with patch('app.SimpleVectorDB') as mock_db_class:
            # Create a mock instance
            mock_instance = MagicMock()
            mock_instance.vectors = {}
            mock_instance.dimension = 3
            mock_instance.generate_embedding.return_value = [0.1, 0.2, 0.3]
            mock_instance.search_similar.return_value = []
            mock_instance.get_stats.return_value = {
                "total_vectors": 0,
                "dimension": 3,
                "model_name": "all-MiniLM-L6-v2"
            }
            mock_instance.get_all_vectors.return_value = {}
            mock_instance.get_vector.return_value = None
            mock_instance.add_vector.return_value = True
            mock_instance.delete_vector.return_value = True
            mock_instance.change_dimension.return_value = True
            mock_instance.regenerate_all_embeddings.return_value = True
            
            # Make the class return our mock instance
            mock_db_class.return_value = mock_instance
            
            # Also patch the global vector_db instance
            with patch('app.vector_db', mock_instance):
                yield mock_instance
    
    def test_health_check(self):
        """Test the health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_stats_endpoint(self, mock_vector_db):
        """Test the stats endpoint returns correct information"""
        mock_vector_db.get_stats.return_value = {
            "total_vectors": 1,
            "dimension": 3,
            "model_name": "all-MiniLM-L6-v2"
        }
        
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "vector_db" in data
        assert data["vector_db"]["total_vectors"] == 1
        assert data["vector_db"]["dimension"] == 3
    
    def test_get_vectors(self, mock_vector_db):
        """Test getting all vectors"""
        mock_vectors = {
            "1": ([0.1, 0.2, 0.3], {"text": "first vector", "type": "test"}),
            "2": ([0.4, 0.5, 0.6], {"text": "second vector", "type": "test"})
        }
        mock_vector_db.get_all_vectors.return_value = mock_vectors
        
        response = client.get("/api/vectors")
        assert response.status_code == 200
        data = response.json()
        
        assert "vectors" in data
        assert len(data["vectors"]) == 2
        assert any(v["text"] == "first vector" for v in data["vectors"])
        assert any(v["text"] == "second vector" for v in data["vectors"])
    
    def test_add_vector(self, mock_vector_db):
        """Test adding a new vector"""
        mock_vector_db.add_vector.return_value = True
        mock_vector_db.get_vector.return_value = ([0.1, 0.2, 0.3], {"text": "new test vector"})
        
        response = client.post(
            "/api/vectors",
            json={"text": "new test vector"}
        )
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "id" in data
        # The add_vector method should be called with the generated id and text
        mock_vector_db.add_vector.assert_called_once()
        # Check that the call was made with the correct arguments
        call_args = mock_vector_db.add_vector.call_args
        assert call_args[0][1] == "new test vector"  # text parameter
    
    def test_get_specific_vector(self, mock_vector_db):
        """Test getting a specific vector by ID"""
        mock_vector_db.get_vector.return_value = ([0.1, 0.2, 0.3], {"text": "test vector"})
        
        response = client.get("/api/vectors/test_id")
        assert response.status_code == 200
        data = response.json()
        
        assert data["text"] == "test vector"
        assert data["vector"] == [0.1, 0.2, 0.3]
    
    def test_get_nonexistent_vector(self, mock_vector_db):
        """Test getting a vector that doesn't exist"""
        mock_vector_db.get_vector.return_value = None
        
        response = client.get("/api/vectors/nonexistent")
        assert response.status_code == 404
    
    def test_delete_vector(self, mock_vector_db):
        """Test deleting a vector"""
        mock_vector_db.delete_vector.return_value = True
        
        response = client.delete("/api/vectors/test_id")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        mock_vector_db.delete_vector.assert_called_once_with("test_id")
    
    def test_delete_nonexistent_vector(self, mock_vector_db):
        """Test deleting a vector that doesn't exist"""
        mock_vector_db.delete_vector.return_value = False
        
        response = client.delete("/api/vectors/nonexistent")
        assert response.status_code == 404
    
    def test_search_vectors(self, mock_vector_db):
        """Test searching for similar vectors"""
        mock_results = [
            ("1", 0.95, {"text": "swimming", "type": "test"}),
            ("2", 0.85, {"text": "diving", "type": "test"})
        ]
        mock_vector_db.search_similar.return_value = mock_results
        mock_vector_db.get_vector.side_effect = [
            ([0.1, 0.2, 0.3], {"text": "swimming"}),
            ([0.4, 0.5, 0.6], {"text": "diving"})
        ]
        
        response = client.post(
            "/api/search",
            json={"query": "swimming", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["text"] == "swimming"
        assert data["results"][0]["similarity"] == 0.95
    
    def test_generate_embedding(self, mock_vector_db):
        """Test generating an embedding for text"""
        mock_vector_db.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        response = client.post(
            "/api/embedding",
            json={"text": "test text"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "embedding" in data
        assert data["embedding"] == [0.1, 0.2, 0.3]
        mock_vector_db.generate_embedding.assert_called_once_with("test text")
    
    def test_change_dimension(self, mock_vector_db):
        """Test changing the dimension of the database"""
        mock_vector_db.change_dimension.return_value = True
        
        response = client.post(
            "/api/change-dimension",
            json={"dimension": 20}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        mock_vector_db.change_dimension.assert_called_once_with(20)
    
    def test_regenerate_embeddings(self, mock_vector_db):
        """Test regenerating all embeddings"""
        mock_vector_db.regenerate_all_embeddings.return_value = True
        mock_vector_db.vectors = {"1": "dummy"}
        
        response = client.post("/api/regenerate")
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        mock_vector_db.regenerate_all_embeddings.assert_called_once()
    
    def test_invalid_dimension_change(self, mock_vector_db):
        """Test changing to an invalid dimension"""
        # The vector_db.change_dimension method doesn't validate dimension values
        # so it will try to create a PCA with 999 components, which will fail
        mock_vector_db.change_dimension.side_effect = Exception("Invalid dimension")
        
        response = client.post(
            "/api/change-dimension",
            json={"dimension": 999}
        )
        assert response.status_code == 500
        data = response.json()
        
        assert "detail" in data
        assert "Error changing dimension" in data["detail"]
    
    def test_search_with_empty_query(self, mock_vector_db):
        """Test search with empty query"""
        response = client.post(
            "/api/search",
            json={"query": "", "top_k": 5}
        )
        # FastAPI doesn't validate empty strings as invalid, so this should work
        assert response.status_code == 200
    
    def test_add_vector_with_empty_text(self, mock_vector_db):
        """Test adding vector with empty text"""
        mock_vector_db.add_vector.return_value = True
        mock_vector_db.get_vector.return_value = ([0.1, 0.2, 0.3], {"text": ""})
        
        response = client.post(
            "/api/vectors",
            json={"text": ""}
        )
        # Empty text is allowed by the API
        assert response.status_code == 201
    
    def test_search_similarity_accuracy(self, mock_vector_db):
        """Test that search returns results in correct similarity order"""
        mock_results = [
            ("1", 0.95, {"text": "swimming", "type": "test"}),
            ("2", 0.85, {"text": "diving", "type": "test"}),
            ("3", 0.45, {"text": "programming", "type": "test"})
        ]
        mock_vector_db.search_similar.return_value = mock_results
        mock_vector_db.get_vector.side_effect = [
            ([0.1, 0.2, 0.3], {"text": "swimming"}),
            ([0.4, 0.5, 0.6], {"text": "diving"}),
            ([0.7, 0.8, 0.9], {"text": "programming"})
        ]
        
        response = client.post(
            "/api/search",
            json={"query": "swimming", "top_k": 3}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Results should be in descending similarity order
        similarities = [r["similarity"] for r in data["results"]]
        assert similarities == sorted(similarities, reverse=True)
        
        # All similarities should be between 0 and 1
        assert all(0 <= sim <= 1 for sim in similarities)
    
    def test_embedding_dimension_consistency(self, mock_vector_db):
        """Test that embeddings maintain consistent dimensions"""
        # Test 3D embeddings
        mock_vector_db.dimension = 3
        mock_vector_db.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        response = client.post(
            "/api/embedding",
            json={"text": "test"}
        )
        assert response.status_code == 200
        embedding = response.json()["embedding"]
        assert len(embedding) == 3
        
        # Test 20D embeddings
        mock_vector_db.dimension = 20
        mock_vector_db.generate_embedding.return_value = [0.1] * 20
        
        response = client.post(
            "/api/embedding",
            json={"text": "test"}
        )
        assert response.status_code == 200
        embedding = response.json()["embedding"]
        assert len(embedding) == 20 