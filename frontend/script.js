// Global variables
let vectors = [];
let searchResults = [];
let currentQueryVector = null;
let svg, simulation;
let tooltip;
let highlightedNodes = new Set();

// API base URL
const API_BASE = 'http://localhost:8000/api';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeVisualization();
    loadVectors();
    loadStats();
    
    // Add event listeners for Enter key
    document.getElementById('newText').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') addVector();
    });
    
    document.getElementById('searchQuery').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') searchVectors();
    });
});

// Initialize D3.js visualization
function initializeVisualization() {
    const container = document.getElementById('visualization');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Create SVG
    svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    

    
    // Create simulation with padding
    simulation = d3.forceSimulation()
        .force('charge', d3.forceManyBody().strength(-80))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(15))
        .force('x', d3.forceX(width / 2).strength(0.1))
        .force('y', d3.forceY(height / 2).strength(0.1))
        .force('padding', function() {
            // Add padding force to keep nodes away from edges
            vectors.forEach(function(d) {
                const padding = 10;
                if (d.x < padding) d.x = padding;
                if (d.x > width - padding) d.x = width - padding;
                if (d.y < padding) d.y = padding;
                if (d.y > height - padding) d.y = height - padding;
            });
        });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        const newWidth = container.clientWidth;
        const newHeight = container.clientHeight;
        svg.attr('width', newWidth).attr('height', newHeight);
        simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
        simulation.alpha(1).restart();
    });
}

// Load vectors from API
async function loadVectors() {
    try {
        const response = await fetch(`${API_BASE}/vectors`);
        const data = await response.json();
        
        vectors = data.vectors.map(vector => ({
            id: vector.id,
            x: vector.vector[0] * 150 + 250, // Scale and center - reduced scale
            y: vector.vector[1] * 150 + 250,
            z: vector.vector[2] * 150 + 250,
            vector: vector.vector,
            text: vector.text,
            type: vector.type,
            timestamp: vector.timestamp,
            metadata: vector.metadata,
            isHighlighted: false
        }));
        
        updateVisualization();
    } catch (error) {
        console.error('Error loading vectors:', error);
    }
}

// Update the 3D visualization
function updateVisualization() {
    // Clear existing elements
    svg.selectAll('*').remove();
    
    // Create nodes
    const nodes = svg.selectAll('.node')
        .data(vectors)
        .enter()
        .append('circle')
        .attr('class', d => `node vector-point ${d.isHighlighted ? 'highlighted' : ''}`)
        .attr('r', 8) // Consistent radius for all nodes
        .attr('fill', '#000') // All vectors are black dots
        .attr('stroke', 'none') // No border
        .attr('opacity', 0.8)
        .on('mouseover', showVectorDetails)
    
    // Add labels for some nodes (avoid clutter)
    const labels = svg.selectAll('.label')
        .data(vectors.filter((d, i) => i < 10)) // Show labels for first 10 nodes
        .enter()
        .append('text')
        .attr('class', 'label')
        .attr('text-anchor', 'middle')
        .attr('dy', -12)
        .attr('font-size', '10px')
        .attr('fill', '#666')
        .text(d => d.text.substring(0, 15) + (d.text.length > 15 ? '...' : ''));
    
    // Update simulation without restarting if it's already running
    simulation.nodes(vectors)
        .on('tick', () => {
            const container = document.getElementById('visualization');
            const width = container.clientWidth;
            const height = container.clientHeight;
            const padding = 10;
            
            nodes
                .attr('cx', d => {
                    // Apply padding constraints
                    d.x = Math.max(padding, Math.min(width - padding, d.x));
                    return d.x;
                })
                .attr('cy', d => {
                    // Apply padding constraints
                    d.y = Math.max(padding, Math.min(height - padding, d.y));
                    return d.y;
                });
            
            labels
                .attr('x', d => Math.max(padding, Math.min(width - padding, d.x)))
                .attr('y', d => Math.max(padding, Math.min(height - padding, d.y)));
        });
    
    // Only restart if simulation is not already running
    if (simulation.alpha() < 0.1) {
        simulation.alpha(0.3).restart();
    }
}

// Get node color based on type
function getNodeColor(d) {
    return '#000'; // All vectors are black
}

// Get node opacity
function getNodeOpacity(d) {
    return 0.8; // Consistent opacity for all nodes
}

// Show vector details in panel on hover
function showVectorDetails(event, d) {
    const detailsHtml = `
        <div class="vector-detail-item">
            <strong>text:</strong> ${d.text}, 
            <strong>vector:</strong> [${d.vector.map(v => v.toFixed(3)).join(', ')}]
        </div>
    `;
    
    document.getElementById('vectorDetails').innerHTML = detailsHtml;
}

// Add new vector
async function addVector() {
    const text = document.getElementById('newText').value.trim();
    if (!text) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/vectors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('newText').value = '';
            
            // Add the new vector to our local array instead of reloading
            const newVector = {
                id: data.id,
                x: data.vector[0] * 150 + 250,
                y: data.vector[1] * 150 + 250,
                z: data.vector[2] * 150 + 250,
                vector: data.vector,
                text: text,
                type: 'document',
                timestamp: new Date().toISOString(),
                metadata: data.metadata || {},
                isHighlighted: false
            };
            
            vectors.push(newVector);
            
            // Update visualization without restarting simulation
            updateVisualization();
            
            // Update stats
            await loadStats();
            
            // Highlight the newly added vector
            highlightVector(newVector.id); // Highlight permanently
            

        } else {
            console.error('Failed to add vector:', data.error);
        }
    } catch (error) {
        console.error('Error adding vector:', error);
    }
}

// Search vectors
async function searchVectors() {
    const query = document.getElementById('searchQuery').value.trim();
    if (!query) {
        return;
    }
    
    try {
        // Clear previous search highlights
        highlightedNodes.clear();
        vectors.forEach(vector => {
            vector.isHighlighted = false;
        });
        svg.selectAll('.node').classed('highlighted', false);
        
        // Get query embedding
        const embeddingResponse = await fetch(`${API_BASE}/embedding`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: query })
        });
        
        const embeddingData = await embeddingResponse.json();
        currentQueryVector = {
            x: embeddingData.embedding[0] * 150 + 250,
            y: embeddingData.embedding[1] * 150 + 250,
            z: embeddingData.embedding[2] * 150 + 250,
            vector: embeddingData.embedding,
            text: query,
            isQueryVector: true
        };
        
        // Search for similar vectors
        const searchResponse = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query, top_k: 5 })
        });
        
        const searchData = await searchResponse.json();
        searchResults = searchData.results;
        
        // Update visualization with search results
        updateVisualizationWithSearch();
        
        // Update search results display
        displaySearchResults(searchData);
        
    } catch (error) {
        console.error('Error searching vectors:', error);
    }
}

// Update visualization with search results
function updateVisualizationWithSearch() {
    // Mark search result nodes as highlighted
    vectors.forEach(vector => {
        vector.isSearchResult = searchResults.some(result => result.id === vector.id);
        // Mark search results as highlighted
        if (vector.isSearchResult) {
            vector.isHighlighted = true;
            highlightedNodes.add(vector.id);
        }
    });
    
    // Force re-render of visualization to apply highlighting
    updateVisualization();
}

// Highlight a specific vector
function highlightVector(vectorId) {
    const vector = vectors.find(v => v.id === vectorId);
    if (!vector) return;
    
    // Add to highlighted set
    highlightedNodes.add(vectorId);
    vector.isHighlighted = true;
    
    // Update the specific node's class without restarting simulation
    svg.selectAll('.node')
        .filter(d => d.id === vectorId)
        .classed('highlighted', true);
}

// Display search results
function displaySearchResults(data) {
    const container = document.getElementById('searchResults');
    
    // Update the search results title with count
    const resultsSection = container.closest('.results-section');
    const titleElement = resultsSection.querySelector('h3');
    titleElement.textContent = `Search Results (${data.count})`;
    
    if (data.results.length === 0) {
        container.innerHTML = '<p>No similar vectors found.</p>';
        return;
    }
    
    // Get the query vector for comparison
    const queryVector = currentQueryVector ? currentQueryVector.vector : null;
    
    // Add query summary
    let querySummary = '';
    if (queryVector) {
        const queryVectorStr = `[${queryVector.map(v => v.toFixed(4)).join(', ')}]`;
        querySummary = `
            <div class="query-summary">
                <div class="query-title"><strong>Search Query:</strong> "${data.query}"</div>
                <div class="query-vector"><strong>Query Vector:</strong> ${queryVectorStr}</div>
            </div>
        `;
    }
    
    const resultsHtml = data.results.map(result => {
        // Calculate vector comparison details
        let comparisonDetails = '';
        if (queryVector && result.vector) {
            const similarities = [];
            for (let i = 0; i < Math.min(queryVector.length, result.vector.length); i++) {
                const queryVal = queryVector[i];
                const resultVal = result.vector[i];
                const contribution = (queryVal * resultVal).toFixed(3);
                const sign = queryVal * resultVal > 0 ? '+' : '';
                similarities.push(`D${i+1}: ${sign}${contribution}`);
            }
            comparisonDetails = similarities.join(', ');
        }
        
        // Format vector coordinates
        const vectorStr = result.vector ? `[${result.vector.map(v => v.toFixed(4)).join(', ')}]` : 'N/A';
        
        // Determine match explanation
        let matchExplanation = '';
        if (result.similarity >= 0.95) {
            matchExplanation = 'Perfect match - identical or very similar text';
        } else if (result.similarity >= 0.8) {
            matchExplanation = 'Strong match - highly similar semantic meaning';
        } else if (result.similarity >= 0.7) {
            matchExplanation = 'Good match - related concepts or similar context';
        } else {
            matchExplanation = 'Weak match - some similarity in vector space';
        }
        
        return `
            <div class="search-result-item">
                <div class="result-title">${result.text.substring(0, 50)}${result.text.length > 50 ? '...' : ''}</div>
                <div class="result-similarity">Similarity: ${(result.similarity * 100).toFixed(1)}%</div>
                <div class="result-text"><strong>Text:</strong> ${result.text}</div>
                <div class="result-vector"><strong>Vector:</strong> ${vectorStr}</div>
                <div class="result-match"><strong>Match Type:</strong> ${matchExplanation}</div>
                ${comparisonDetails ? `<div class="result-comparison"><strong>Dimension Similarities:</strong> ${comparisonDetails}</div>` : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = querySummary + resultsHtml;
}

// Clear search
function clearSearch() {
    searchResults = [];
    currentQueryVector = null;
    
    // Clear all highlights
    highlightedNodes.clear();
    
    // Reset vectors
    vectors.forEach(vector => {
        vector.isSearchResult = false;
        vector.isQueryVector = false;
        vector.isHighlighted = false;
    });
    
    // Update visualization without restarting simulation
    svg.selectAll('.node')
        .classed('highlighted', false);
    
    // Clear displays
    document.getElementById('searchResults').innerHTML = '...';
    document.getElementById('searchQuery').value = '';
    
    // Reset the search results title
    const resultsSection = document.getElementById('searchResults').closest('.results-section');
    const titleElement = resultsSection.querySelector('h3');
    titleElement.textContent = 'Search Results';
}

// Reset view
function resetView() {
    simulation.alpha(1).restart();
}

// Load system stats
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        const statsHtml = `
            <div class="stat-item">
                <span class="stat-label">Total Vectors:</span>
                <span class="stat-value">${data.vector_db.total_vectors}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Dimension:</span>
                <span class="stat-value">${data.vector_db.dimension}D</span>
            </div>
        `;
        
        document.getElementById('stats').innerHTML = statsHtml;
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stats').innerHTML = '<div>Failed to load stats</div>';
    }
}

// Utility functions 