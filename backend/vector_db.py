import json
import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import os
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
import pickle

class SimpleVectorDB:
    def __init__(self, dimension: int = 3, storage_file: str = "vector_db.json", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize a simple vector database with sentence-transformers and PCA.
        Default dimension is 3 for easy 3D visualization.
        """
        self.dimension = dimension
        self.storage_file = storage_file
        self.model_name = model_name
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict] = {}
        
        # Initialize the sentence transformer model
        print(f"Loading sentence transformer model: {model_name}")
        print("This may take 10-30 seconds on first run as the model downloads...")
        self.model = SentenceTransformer(model_name, device='cpu')  # Force CPU for consistency
        self.original_dimension = self.model.get_sentence_embedding_dimension()
        print(f"✅ Model loaded successfully!")
        print(f"   Model: {model_name}")
        print(f"   Original dimension: {self.original_dimension}")
        print(f"   Target dimension: {self.dimension}")
        
        # Initialize PCA for dimensionality reduction
        self.pca = PCA(n_components=dimension)
        self.pca_fitted = False
        
        self.load_data()
    
    def load_data(self):
        """Load existing data from storage file if it exists."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.vectors = data.get('vectors', {})
                    self.metadata = data.get('metadata', {})
                
                # Load PCA model if it exists
                pca_file = self.storage_file.replace('.json', '_pca.pkl')
                if os.path.exists(pca_file):
                    with open(pca_file, 'rb') as f:
                        self.pca = pickle.load(f)
                        self.pca_fitted = True
                        print("PCA model loaded from file")
                
                print(f"Loaded {len(self.vectors)} vectors from storage")
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
            
            # Save PCA model
            pca_file = self.storage_file.replace('.json', '_pca.pkl')
            with open(pca_file, 'wb') as f:
                pickle.dump(self.pca, f)
                
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using sentence-transformers and reduce to 3D using PCA.
        """
        # Generate embedding using the sentence transformer model
        embedding = self.model.encode(text, show_progress_bar=False)
        
        # Convert to numpy array and reshape for PCA
        embedding_array = np.array(embedding).reshape(1, -1)
        
        # If PCA is not fitted yet, we need at least n_components samples to fit PCA
        if not self.pca_fitted:
            # For the first few embeddings, we'll use a simple approach
            # We'll create dummy embeddings by adding small noise
            # We need at least n_components samples
            num_dummy_samples = max(self.dimension - 1, 2)  # At least 2 dummy samples
            combined_embeddings = [embedding_array]
            
            for i in range(num_dummy_samples):
                dummy_embedding = embedding_array + np.random.normal(0, 0.01, embedding_array.shape)
                combined_embeddings.append(dummy_embedding)
            
            combined_embeddings = np.vstack(combined_embeddings)
            
            print(f"Fitting PCA model with {len(combined_embeddings)} samples for {self.dimension} components...")
            self.pca.fit(combined_embeddings)
            self.pca_fitted = True
            print("✅ PCA model fitted successfully")
        
        # Transform to 3D
        reduced_embedding = self.pca.transform(embedding_array)[0]
        
        # Scale the values by 10x to make them more visible in visualization
        scaled_embedding = reduced_embedding * 10
        
        # Convert to list and round for storage
        return [round(float(x), 4) for x in scaled_embedding]
    
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
            'type': 'document',
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
    
    def search_similar(self, query_text: str, top_k: int = 5, threshold: float = 0.0) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar vectors using cosine similarity.
        Returns list of (id, similarity_score, metadata) tuples.
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
        
        # Convert to numpy arrays for efficient computation
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        magnitude1 = np.linalg.norm(vec1_array)
        magnitude2 = np.linalg.norm(vec2_array)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return float(dot_product / (magnitude1 * magnitude2))
    
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
            'original_dimension': self.original_dimension,
            'model_name': self.model_name,
            'pca_fitted': self.pca_fitted,
            'storage_file': self.storage_file
        }
    
    def regenerate_all_embeddings(self) -> bool:
        """
        Regenerate all embeddings with the current PCA model and scaling.
        This is useful when the PCA model or scaling factor changes.
        """
        if not self.pca_fitted:
            print("PCA model not fitted yet. Cannot regenerate embeddings.")
            return False
        
        print(f"Regenerating {len(self.vectors)} embeddings with new scaling...")
        
        # Store original texts
        original_texts = {id: self.metadata[id]['text'] for id in self.vectors.keys()}
        
        # Clear existing vectors
        self.vectors.clear()
        
        # Regenerate embeddings for all texts
        for id, text in original_texts.items():
            embedding = self.generate_embedding(text)
            self.vectors[id] = embedding
        
        # Save the updated data
        self.save_data()
        print("✅ All embeddings regenerated successfully")
        return True
    
    def change_dimension(self, new_dimension: int) -> bool:
        """
        Change the PCA dimension and regenerate all embeddings.
        """
        if new_dimension == self.dimension:
            return True  # No change needed
        
        if new_dimension > self.original_dimension:
            print(f"Error: New dimension ({new_dimension}) cannot exceed original dimension ({self.original_dimension})")
            return False
        
        print(f"Changing dimension from {self.dimension} to {new_dimension}...")
        
        # Store original texts
        original_texts = {id: self.metadata[id]['text'] for id in self.vectors.keys()}
        
        # Update dimension and PCA
        self.dimension = new_dimension
        self.pca = PCA(n_components=self.dimension)
        self.pca_fitted = False
        
        # Clear existing vectors
        self.vectors.clear()
        
        # Regenerate embeddings for all texts with new dimension
        for id, text in original_texts.items():
            embedding = self.generate_embedding(text)
            self.vectors[id] = embedding
        
        # Save the updated data
        self.save_data()
        print(f"✅ Dimension changed to {new_dimension} and all embeddings regenerated")
        return True 