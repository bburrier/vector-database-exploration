#!/usr/bin/env python3
"""
Startup script for the RAG Vector Database Backend
"""

import os
import sys
import subprocess
import time

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        sys.exit(1)

def install_requirements():
    """Install required packages."""
    print("Installing required packages...")
    try:
        # Get the project root directory (two levels up from scripts/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        requirements_path = os.path.join(project_root, "backend", "requirements.txt")
        
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
        print("✓ Packages installed successfully")
    except subprocess.CalledProcessError:
        print("Error: Failed to install packages")
        sys.exit(1)

def start_server():
    """Start the FastAPI server."""
    print("Starting Vector Database API Server...")
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Get the project root directory and change to backend directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_dir = os.path.join(project_root, "backend")
        os.chdir(backend_dir)
        
        # Start FastAPI server with uvicorn
        subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print("Vector Database Explorer - Backend Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if backend directory exists
    backend_dir = os.path.join(project_root, "backend")
    if not os.path.exists(backend_dir):
        print("Error: Backend directory not found")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    # Check if requirements.txt exists
    requirements_path = os.path.join(backend_dir, "requirements.txt")
    if not os.path.exists(requirements_path):
        print("Error: requirements.txt not found in backend directory")
        sys.exit(1)
    
    # Install requirements
    install_requirements()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main() 