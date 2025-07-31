#!/usr/bin/env python3
"""
Performance test script for embedding generation.
"""

import time
import sys
import os

def test_embedding_performance():
    """Test the performance of embedding generation."""
    print("🚀 Testing Embedding Performance")
    print("=" * 50)
    
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.decomposition import PCA
        import numpy as np
        
        # Test with the smaller model
        model_name = "all-MiniLM-L6-v2"
        print(f"Loading model: {model_name}")
        
        start_time = time.time()
        model = SentenceTransformer(model_name, device='cpu')
        load_time = time.time() - start_time
        
        print(f"✅ Model loaded in {load_time:.2f} seconds")
        print(f"   Original dimension: {model.get_sentence_embedding_dimension()}")
        
        # Test embedding generation
        test_texts = [
            "hello",
            "world", 
            "machine learning",
            "artificial intelligence",
            "vector database"
        ]
        
        # Initialize PCA
        pca = PCA(n_components=3)
        pca_fitted = False
        
        print(f"\n📊 Testing embedding generation:")
        print("-" * 30)
        
        # First, collect all embeddings to fit PCA properly
        all_embeddings = []
        for text in test_texts:
            embedding = model.encode(text, show_progress_bar=False)
            all_embeddings.append(embedding)
        
        # Fit PCA with all embeddings
        embeddings_array = np.array(all_embeddings)
        pca.fit(embeddings_array)
        print(f"   PCA fitted with {len(test_texts)} samples")
        
        # Now test individual embeddings
        for i, text in enumerate(test_texts):
            start_time = time.time()
            
            # Generate embedding (should be fast now)
            embedding = model.encode(text, show_progress_bar=False)
            embed_time = time.time() - start_time
            
            # PCA reduction
            start_time = time.time()
            embedding_array = np.array(embedding).reshape(1, -1)
            reduced = pca.transform(embedding_array)
            pca_time = time.time() - start_time
            
            total_time = embed_time + pca_time
            
            print(f"   '{text}': {total_time:.3f}s ({embedding_array.shape[1]}D → 3D)")
        
        print(f"\n✅ Performance Summary:")
        print(f"   Model load time: {load_time:.2f}s (one-time)")
        print(f"   Average embedding time: ~{(total_time/len(test_texts)):.3f}s per text")
        print(f"   Expected speed after warmup: 5-20ms per embedding")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install dependencies with: pip install sentence-transformers scikit-learn torch")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_embedding_performance()
    if success:
        print(f"\n🎉 Performance test completed successfully!")
    else:
        print(f"\n💥 Performance test failed!")
        sys.exit(1) 