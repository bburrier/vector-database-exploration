import json
import math
import random
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import os

class SimpleVectorDB:
    def __init__(self, dimension: int = 3, storage_file: str = "vector_db.json"):
        """
        Initialize a simple vector database with specified dimension.
        Default dimension is 3 for easy 3D visualization.
        """
        self.dimension = dimension
        self.storage_file = storage_file
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict] = {}
        self.load_data()
    
    def load_data(self):
        """Load existing data from storage file if it exists."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.vectors = data.get('vectors', {})
                    self.metadata = data.get('metadata', {})
            except Exception as e:
                print(f"Error loading data: {e}")
                self.vectors = {}
                self.metadata = {}
    
    def save_data(self):
        """Save data to storage file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({
                    'vectors': self.vectors,
                    'metadata': self.metadata
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a simple embedding for text using a deterministic hash-based approach.
        This is a simplified embedding - in real systems you'd use proper embedding models.
        """
        # Create a deterministic hash by using the text bytes
        import hashlib
        hash_bytes = hashlib.md5(text.encode('utf-8')).digest()
        
        # Convert bytes to a deterministic seed
        seed = int.from_bytes(hash_bytes[:4], byteorder='big')
        random.seed(seed)
        
        # Generate 3D vector with values between -1 and 1
        embedding = []
        for i in range(self.dimension):
            val = random.uniform(-1, 1)
            embedding.append(round(val, 4))
        
        return embedding
    
    def add_vector(self, id: str, text: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add a new vector to the database.
        """
        if id in self.vectors:
            return False  # ID already exists
        
        embedding = self.generate_embedding(text)
        self.vectors[id] = embedding
        self.metadata[id] = {
            'text': text,
            'timestamp': self._get_timestamp(),
            **(metadata or {})
        }
        self.save_data()
        return True
    
    def get_vector(self, id: str) -> Optional[Tuple[List[float], Dict]]:
        """
        Retrieve a vector and its metadata by ID.
        """
        if id not in self.vectors:
            return None
        return self.vectors[id], self.metadata[id]
    
    def search_similar(self, query_text: str, top_k: int = 5, threshold: float = 0.7) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar vectors using cosine similarity.
        Returns list of (id, similarity_score, metadata) tuples.
        Only returns vectors with similarity above the threshold.
        """
        query_embedding = self.generate_embedding(query_text)
        
        similarities = []
        for id, vector in self.vectors.items():
            similarity = self._cosine_similarity(query_embedding, vector)
            # Only include vectors above the similarity threshold
            if similarity >= threshold:
                similarities.append((id, similarity, self.metadata[id]))
        
        # Sort by similarity (descending) and return top_k results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_all_vectors(self) -> Dict[str, Tuple[List[float], Dict]]:
        """
        Get all vectors and their metadata.
        """
        return {id: (vector, self.metadata[id]) for id, vector in self.vectors.items()}
    
    def delete_vector(self, id: str) -> bool:
        """
        Delete a vector from the database.
        """
        if id not in self.vectors:
            return False
        
        del self.vectors[id]
        del self.metadata[id]
        self.save_data()
        return True
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_stats(self) -> Dict:
        """
        Get database statistics.
        """
        return {
            'total_vectors': len(self.vectors),
            'dimension': self.dimension,
            'storage_file': self.storage_file
        } 