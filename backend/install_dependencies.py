#!/usr/bin/env python3
"""
Script to install dependencies and test the sentence-transformers setup.
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install the required dependencies."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    return True

def test_sentence_transformers():
    """Test if sentence-transformers is working correctly."""
    print("\nTesting sentence-transformers...")
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Test with a small model first
        print("Loading test model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Test embedding generation
        test_text = "Hello world"
        embedding = model.encode(test_text)
        
        print(f"✅ Sentence-transformers working!")
        print(f"   Model: all-MiniLM-L6-v2")
        print(f"   Original dimension: {len(embedding)}")
        print(f"   Test embedding shape: {embedding.shape}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing sentence-transformers: {e}")
        return False

def test_pca():
    """Test PCA functionality."""
    print("\nTesting PCA...")
    try:
        from sklearn.decomposition import PCA
        import numpy as np
        
        # Create test data
        test_data = np.random.rand(10, 768)  # 10 samples, 768 dimensions
        pca = PCA(n_components=3)
        
        # Fit and transform
        reduced_data = pca.fit_transform(test_data)
        
        print(f"✅ PCA working!")
        print(f"   Original shape: {test_data.shape}")
        print(f"   Reduced shape: {reduced_data.shape}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing PCA: {e}")
        return False

def main():
    """Main function to run all tests."""
    print("🚀 Setting up Vector Database with Sentence-Transformers")
    print("=" * 60)
    
    # Install dependencies
    if not install_dependencies():
        print("Failed to install dependencies. Exiting.")
        return
    
    # Test sentence-transformers
    if not test_sentence_transformers():
        print("Failed to test sentence-transformers. Exiting.")
        return
    
    # Test PCA
    if not test_pca():
        print("Failed to test PCA. Exiting.")
        return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! The system is ready to use.")
    print("\nYou can now start the server with:")
    print("  python app.py")
    print("\nThe system will:")
    print("  - Use sentence-transformers for real LLM embeddings")
    print("  - Reduce embeddings to 3D using PCA for visualization")
    print("  - Provide semantic search capabilities")

if __name__ == "__main__":
    main() 