from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import uuid
import os
from datetime import datetime
from vector_db import SimpleVectorDB

# Initialize FastAPI app
app = FastAPI(
    title="Vector Database API",
    description="A simple vector database API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the vector database with sentence-transformers
vector_db = SimpleVectorDB(dimension=3, storage_file="vector_db.json", model_name="all-MiniLM-L6-v2")

# Ensure existing vectors are in 3D format
if vector_db.vectors:
    # Check if any existing vectors are not 3D
    sample_vector = next(iter(vector_db.vectors.values()))
    if len(sample_vector) != 3:
        print(f"Found {len(vector_db.vectors)} vectors in {len(sample_vector)}D format, regenerating in 3D...")
        vector_db.regenerate_all_embeddings()
    else:
        print(f"All {len(vector_db.vectors)} vectors are already in 3D format")

# Pydantic models for request/response
class VectorRequest(BaseModel):
    text: str
    id: Optional[str] = None
    metadata: Optional[Dict] = None

class VectorResponse(BaseModel):
    success: bool
    id: str
    vector: List[float]
    text: str
    metadata: Dict

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SearchResult(BaseModel):
    id: str
    similarity: float
    text: str
    type: str
    timestamp: str
    vector: List[float]
    metadata: Dict

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    count: int

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]
    dimension: int

class StatsResponse(BaseModel):
    vector_db: Dict

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    system: str

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        system="Vector Database API"
    )

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    stats = vector_db.get_stats()
    return StatsResponse(
        vector_db=stats
    )

@app.get("/api/vectors")
async def get_all_vectors():
    """Get all vectors in the database."""
    all_vectors = vector_db.get_all_vectors()
    formatted_vectors = []
    
    for vector_id, (vector, metadata) in all_vectors.items():
        formatted_vectors.append({
            'id': vector_id,
            'vector': vector,
            'text': metadata['text'],
            'type': metadata.get('type', 'unknown'),
            'timestamp': metadata.get('timestamp', ''),
            'metadata': metadata
        })
    
    return {
        'vectors': formatted_vectors,
        'count': len(formatted_vectors)
    }

@app.post("/api/vectors", response_model=VectorResponse, status_code=201)
async def add_vector(request: VectorRequest):
    """Add a new vector to the database."""
    vector_id = request.id or f"doc_{uuid.uuid4().hex[:8]}"
    
    success = vector_db.add_vector(vector_id, request.text, request.metadata)
    
    if not success:
        raise HTTPException(status_code=409, detail="Vector ID already exists")
    
    # Get the added vector for response
    vector_data = vector_db.get_vector(vector_id)
    if vector_data:
        vector, metadata = vector_data
        return VectorResponse(
            success=True,
            id=vector_id,
            vector=vector,
            text=request.text,
            metadata=metadata
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve added vector")

@app.get("/api/vectors/{vector_id}")
async def get_vector(vector_id: str):
    """Get a specific vector by ID."""
    vector_data = vector_db.get_vector(vector_id)
    
    if not vector_data:
        raise HTTPException(status_code=404, detail="Vector not found")
    
    vector, metadata = vector_data
    return {
        'id': vector_id,
        'vector': vector,
        'text': metadata['text'],
        'metadata': metadata
    }

@app.delete("/api/vectors/{vector_id}")
async def delete_vector(vector_id: str):
    """Delete a vector by ID."""
    success = vector_db.delete_vector(vector_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Vector not found")
    
    return {'success': True, 'message': 'Vector deleted'}

@app.post("/api/search", response_model=SearchResponse)
async def search_vectors(request: SearchRequest):
    """Search for similar vectors."""
    results = vector_db.search_similar(request.query, request.top_k)
    
    formatted_results = []
    for item_id, similarity, metadata in results:
        # Get the actual vector coordinates
        vector_data = vector_db.get_vector(item_id)
        vector_coords = vector_data[0] if vector_data else []
        
        formatted_results.append(SearchResult(
            id=item_id,
            similarity=similarity,
            text=metadata['text'],
            type=metadata.get('type', 'unknown'),
            timestamp=metadata.get('timestamp', ''),
            vector=vector_coords,
            metadata=metadata
        ))
    
    return SearchResponse(
        query=request.query,
        results=formatted_results,
        count=len(formatted_results)
    )

@app.post("/api/embedding", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for given text."""
    embedding = vector_db.generate_embedding(request.text)
    
    return EmbeddingResponse(
        text=request.text,
        embedding=embedding,
        dimension=len(embedding)
    )

@app.post("/api/regenerate")
async def regenerate_embeddings():
    """Regenerate all embeddings with current PCA model and scaling."""
    try:
        success = vector_db.regenerate_all_embeddings()
        if success:
            return {
                'success': True,
                'message': 'All embeddings regenerated successfully',
                'count': len(vector_db.vectors)
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to regenerate embeddings")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating embeddings: {str(e)}")

@app.post("/api/change-dimension")
async def change_dimension(request: dict):
    """Change PCA dimension and regenerate all embeddings."""
    try:
        new_dimension = request.get('dimension')
        if new_dimension not in [3, 20]:
            raise HTTPException(status_code=400, detail="Dimension must be 3 or 20")
        
        success = vector_db.change_dimension(new_dimension)
        if success:
            return {
                'success': True,
                'message': f'Dimension changed to {new_dimension}',
                'dimension': new_dimension,
                'count': len(vector_db.vectors)
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to change dimension")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error changing dimension: {str(e)}")

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    frontend_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")

if __name__ == "__main__":
    import uvicorn
    print("Starting Vector Database API Server...")
    print("Available endpoints:")
    print("  GET  /api/health - Health check")
    print("  GET  /api/stats - System statistics")
    print("  GET  /api/vectors - Get all vectors")
    print("  POST /api/vectors - Add new vector")
    print("  GET  /api/vectors/{id} - Get specific vector")
    print("  DELETE /api/vectors/{id} - Delete vector")
    print("  POST /api/search - Search vectors")
    print("  POST /api/embedding - Generate embedding")
    print("\nAPI Documentation available at:")
    print("  http://localhost:8000/docs - Swagger UI")
    print("  http://localhost:8000/redoc - ReDoc")
    print("\nServer starting on http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 