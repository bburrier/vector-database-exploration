#!/usr/bin/env python3
"""
Startup script for the RAG Vector Database Frontend
"""

import os
import sys
import subprocess
import webbrowser
import time

def check_frontend_files():
    """Check if frontend files exist."""
    # Get the project root directory (two levels up from scripts/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    required_files = [
        os.path.join(project_root, "frontend", "index.html"),
        os.path.join(project_root, "frontend", "styles.css"),
        os.path.join(project_root, "frontend", "script.js")
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"Error: {file_path} not found")
            return False
    return True

def start_frontend_server():
    """Start a simple HTTP server for the frontend."""
    print("Starting Vector Database Frontend Server...")
    print("Frontend will be available at: http://localhost:3000")
    print("\nMake sure the backend server is running on http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Get the project root directory and change to frontend directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_dir = os.path.join(project_root, "frontend")
        os.chdir(frontend_dir)
        
        # Start HTTP server
        subprocess.run([sys.executable, "-m", "http.server", "3000"])
    except KeyboardInterrupt:
        print("\n\nFrontend server stopped by user")
    except Exception as e:
        print(f"Error starting frontend server: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print("Vector Database Explorer - Frontend Setup")
    print("=" * 50)
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if frontend directory exists
    frontend_dir = os.path.join(project_root, "frontend")
    if not os.path.exists(frontend_dir):
        print("Error: Frontend directory not found")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    # Check if required frontend files exist
    if not check_frontend_files():
        print("Error: Required frontend files not found")
        sys.exit(1)
    
    print("✓ Frontend files found")
    
    # Start frontend server
    start_frontend_server()

if __name__ == "__main__":
    main() 