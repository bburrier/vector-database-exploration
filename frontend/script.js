// Global variables
let vectors = [];
let searchResults = [];
let currentQueryVector = null;
let scene, camera, renderer, controls;
let points = [];
let labels = [];
let pointMeshes = []; // Separate array for actual point meshes (for raycaster)
let highlightedPoints = new Set();
let dataBounds = { min: { x: 0, y: 0, z: 0 }, max: { x: 0, y: 0, z: 0 } };
let currentDimension = 3;
let radarChart = null;

// Default camera position constant
const DEFAULT_CAMERA_POSITION = [1.6, 0.1, 2.9];

// API base URL - automatically detect environment
// If accessed via ngrok (HTTPS), use relative paths
// If accessed via localhost:3000 (development), use backend URL
const API_BASE = window.location.protocol === 'https:' ? '/api' : 'http://localhost:8000/api';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Ensure we start with 3D visualization
    currentDimension = 3;
    document.getElementById('dimensionToggle').value = '3';
    
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

// Change visualization dimension
async function changeDimension() {
    const newDimension = parseInt(document.getElementById('dimensionToggle').value);
    
    if (newDimension === currentDimension) {
        return; // No change needed
    }
    
    try {
        const response = await fetch(`${API_BASE}/change-dimension`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ dimension: newDimension })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentDimension = newDimension;
            
            // Reload vectors with new dimension
            await loadVectors();
            
            // Update visualization based on new dimension
            if (currentDimension === 3) {
                show3DVisualization();
            } else {
                showRadarChart();
            }
            
            // Re-trigger search if there's an active search
            const searchQuery = document.getElementById('searchQuery').value.trim();
            if (searchQuery && searchResults.length > 0) {
                console.log('Re-triggering search with new dimension...');
                await searchVectors();
            }
            
            // Update stats
            await loadStats();
            
            console.log(`Dimension changed to ${newDimension}`);
        } else {
            console.error('Failed to change dimension:', data.error);
        }
    } catch (error) {
        console.error('Error changing dimension:', error);
    }
}

// Initialize Three.js 3D visualization
function initializeVisualization() {
    const container = document.getElementById('visualization');
    
    // Calculate available space with 1rem margin
    const margin = 16; // 1rem = 16px
    const width = container.clientWidth - (margin * 2);
    const height = container.clientHeight - (margin * 2);
    
    // Create scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);
    
    // Create camera
    camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    // Camera position: (X, Y, Z)
    // X: Positive = right, Negative = left
    // Y: Positive = up, Negative = down (looking up at cube)
    // Z: Positive = forward, Negative = backward
    // Distance from origin = sqrt(X² + Y² + Z²) - increase for less zoom, decrease for more zoom
    // For rotation: adjust X/Z ratio (X/Z = tan(angle))
    camera.position.set(DEFAULT_CAMERA_POSITION[0], DEFAULT_CAMERA_POSITION[1], DEFAULT_CAMERA_POSITION[2]);
    
    // Create renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.domElement.style.margin = '1rem';
    container.appendChild(renderer.domElement);
    
    // Add camera position display
    addCameraPositionDisplay();
    
    // Add controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    
    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 1, 1);
    scene.add(directionalLight);
    
    // Add grid lines for perspective
    addGridLines();
    
    // Handle window resize
    window.addEventListener('resize', function() {
        const margin = 16; // 1rem = 16px
        const newWidth = container.clientWidth - (margin * 2);
        const newHeight = container.clientHeight - (margin * 2);
        
        camera.aspect = newWidth / newHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(newWidth, newHeight);
    });
    
    // Start animation loop
    animate();
}

// Calculate data boundaries for all vectors
function calculateDataBounds() {
    const allVectors = [...vectors];
    if (currentQueryVector) {
        allVectors.push(currentQueryVector);
    }
    
    if (allVectors.length === 0) {
        // Default bounds if no data
        dataBounds = { min: { x: -1, y: -1, z: -1 }, max: { x: 1, y: 1, z: 1 } };
        return;
    }
    
    // Initialize bounds with first vector
    const firstVector = allVectors[0];
    dataBounds = {
        min: { x: firstVector.x, y: firstVector.y, z: firstVector.z },
        max: { x: firstVector.x, y: firstVector.y, z: firstVector.z }
    };
    
    // Find min/max for all vectors
    allVectors.forEach(vector => {
        dataBounds.min.x = Math.min(dataBounds.min.x, vector.x);
        dataBounds.min.y = Math.min(dataBounds.min.y, vector.y);
        dataBounds.min.z = Math.min(dataBounds.min.z, vector.z);
        dataBounds.max.x = Math.max(dataBounds.max.x, vector.x);
        dataBounds.max.y = Math.max(dataBounds.max.y, vector.y);
        dataBounds.max.z = Math.max(dataBounds.max.z, vector.z);
    });
    
    // Add some padding to the bounds
    const padding = 0.1; // 10% padding
    const xRange = dataBounds.max.x - dataBounds.min.x;
    const yRange = dataBounds.max.y - dataBounds.min.y;
    const zRange = dataBounds.max.z - dataBounds.min.z;
    
    dataBounds.min.x -= xRange * padding;
    dataBounds.min.y -= yRange * padding;
    dataBounds.min.z -= zRange * padding;
    dataBounds.max.x += xRange * padding;
    dataBounds.max.y += yRange * padding;
    dataBounds.max.z += zRange * padding;
    
    // Debug: log the calculated bounds
    console.log('Data bounds calculated:', dataBounds);
}

// Normalize a value to -1 to 1 range based on data bounds
function normalizeValue(value, axis) {
    const range = dataBounds.max[axis] - dataBounds.min[axis];
    if (range === 0) return 0;
    return ((value - dataBounds.min[axis]) / range) * 2 - 1;
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
    
    // Update camera position display
    updateCameraPositionDisplay();
}

// Add bounding cube for perspective
function addGridLines() {
    // Create bounding cube based on data bounds
    // Use a default size if no data is loaded yet
    const cubeSize = 2; // Default size for -1 to 1 range
    const cubeGeometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);
    const cubeMaterial = new THREE.MeshBasicMaterial({ 
        color: 0x444444, 
        transparent: true, 
        opacity: 0.1,
        wireframe: true
    });
    const cube = new THREE.Mesh(cubeGeometry, cubeMaterial);
    scene.add(cube);
}

// Update bounding cube based on current data bounds
function updateBoundingCube() {
    // Remove existing cube
    scene.children = scene.children.filter(child => 
        !(child instanceof THREE.Mesh && child.geometry instanceof THREE.BoxGeometry)
    );
    
    // Always create a cube that fits the normalized coordinate system (-1 to 1)
    // Since we normalize all points to -1 to 1 range, the cube should be 2x2x2
    const cubeSize = 2.2; // Slightly larger than the -1 to 1 range for padding
    
    const cubeGeometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);
    const cubeMaterial = new THREE.MeshBasicMaterial({ 
        color: 0x444444, 
        transparent: true, 
        opacity: 0.1,
        wireframe: true
    });
    const cube = new THREE.Mesh(cubeGeometry, cubeMaterial);
    scene.add(cube);
}

// Add camera position display
function addCameraPositionDisplay() {
    const container = document.getElementById('visualization');
    
    // Create position display element
    const positionDisplay = document.createElement('div');
    positionDisplay.id = 'cameraPositionDisplay';
    positionDisplay.style.cssText = `
        position: absolute;
        bottom: 10px;
        right: 10px;
        color: #CCC;
        padding: 5px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 9px;
        z-index: 1000;
        pointer-events: none;
    `;
    positionDisplay.textContent = 'camera: (0, 0, 0)';
    
    container.appendChild(positionDisplay);
}

// Update camera position display
function updateCameraPositionDisplay() {
    const display = document.getElementById('cameraPositionDisplay');
    if (display && camera) {
        const x = camera.position.x.toFixed(1);
        const y = camera.position.y.toFixed(1);
        const z = camera.position.z.toFixed(1);
        display.textContent = `camera: (${x}, ${y}, ${z})`;
    }
}

// Add text label for a vector
function addTextLabel(vector, x, y, z) {
    // Create a canvas for the text
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 768; // 3x larger
    canvas.height = 192; // 3x larger
    
    // Set text properties
    context.fillStyle = '#000000';
    context.font = '72px Arial'; // 3x larger (24 * 3 = 72)
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    
    // Draw text
    const text = vector.text.substring(0, 15) + (vector.text.length > 15 ? '...' : '');
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    
    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas);
    
    // Create sprite material
    const spriteMaterial = new THREE.SpriteMaterial({ 
        map: texture,
        transparent: true,
        opacity: 0.8
    });
    
    // Create sprite (always faces camera)
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.position.set(x + 0.3, y + 0.3, z + 0.3); // Offset further from point to avoid overlap
    sprite.scale.set(1.5, 0.375, 1); // 3x larger scale
    // Sprites automatically face the camera by default
    
    // Add to scene and labels array
    scene.add(sprite);
    labels.push(sprite);
}

// Load vectors from API
async function loadVectors() {
    try {
        const response = await fetch(`${API_BASE}/vectors`);
        const data = await response.json();
        
        vectors = data.vectors.map(vector => ({
            id: vector.id,
            x: vector.vector[0], // Use raw vector values directly
            y: vector.vector[1],
            z: vector.vector[2],
            vector: vector.vector,
            text: vector.text,
            type: vector.type,
            timestamp: vector.timestamp,
            metadata: vector.metadata,
            isHighlighted: false
        }));
        
        // Update visualization based on current mode
        if (currentDimension === 3) {
            updateVisualization();
        } else {
            showRadarChart();
        }
    } catch (error) {
        console.error('Error loading vectors:', error);
    }
}

// Show 3D visualization
function show3DVisualization() {
    const container = document.getElementById('visualization');
    container.innerHTML = ''; // Clear container
    
    // Reinitialize Three.js
    initializeVisualization();
    updateVisualization();
}

// Show radar chart visualization
function showRadarChart() {
    const container = document.getElementById('visualization');
    container.innerHTML = ''; // Clear container
    
    // Create SVG for radar chart
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const width = container.clientWidth - margin.left - margin.right;
    const height = container.clientHeight - margin.top - margin.bottom;
    
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left + width/2},${margin.top + height/2})`);
    
    // Calculate radius based on container size
    const radius = Math.min(width, height) / 2 - 40;
    
    // Create radar chart
    createRadarChart(svg, radius);
}

// Create radar chart
function createRadarChart(svg, radius) {
    const allVectors = [...vectors];
    if (currentQueryVector) {
        allVectors.push(currentQueryVector);
    }
    
    if (allVectors.length === 0) return;
    
    // Get the number of dimensions from the first vector
    const numDimensions = allVectors[0].vector.length;
    
    // Create angle scale
    const angleScale = d3.scalePoint()
        .domain(d3.range(numDimensions))
        .range([0, 2 * Math.PI]);
    
    // Calculate bounds for each dimension
    const dimensionBounds = [];
    for (let i = 0; i < numDimensions; i++) {
        const values = allVectors.map(v => v.vector[i]);
        dimensionBounds.push({
            min: Math.min(...values),
            max: Math.max(...values)
        });
    }
    
    // Create radius scale for each dimension
    const radiusScales = dimensionBounds.map(bounds => 
        d3.scaleLinear()
            .domain([bounds.min, bounds.max])
            .range([0, radius])
    );
    
    // Draw grid circles
    const gridLevels = 5;
    for (let i = 1; i <= gridLevels; i++) {
        const gridRadius = (radius / gridLevels) * i;
        svg.append('circle')
            .attr('cx', 0)
            .attr('cy', 0)
            .attr('r', gridRadius)
            .attr('fill', 'none')
            .attr('stroke', '#ddd')
            .attr('stroke-width', 1);
    }
    
    // Draw dimension axes
    for (let i = 0; i < numDimensions; i++) {
        const angle = angleScale(i);
        const x = Math.cos(angle - Math.PI/2) * radius;
        const y = Math.sin(angle - Math.PI/2) * radius;
        
        // Draw axis line
        svg.append('line')
            .attr('x1', 0)
            .attr('y1', 0)
            .attr('x2', x)
            .attr('y2', y)
            .attr('stroke', '#999')
            .attr('stroke-width', 1);
        
        // Add dimension label
        svg.append('text')
            .attr('x', Math.cos(angle - Math.PI/2) * (radius + 20))
            .attr('y', Math.sin(angle - Math.PI/2) * (radius + 20))
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('font-size', '12px')
            .attr('fill', '#666')
            .text(`D${i+1}`);
    }
    
    // Draw vector polygons
    allVectors.forEach((vector, index) => {
        const points = [];
        for (let i = 0; i < numDimensions; i++) {
            const angle = angleScale(i);
            const value = vector.vector[i];
            const r = radiusScales[i](value);
            const x = Math.cos(angle - Math.PI/2) * r;
            const y = Math.sin(angle - Math.PI/2) * r;
            points.push([x, y]);
        }
        
        // Create polygon
        const polygon = svg.append('polygon')
            .attr('points', points.map(p => p.join(',')).join(' '))
            .attr('fill', vector.isQueryVector ? '#a081d9' : '#000')
            .attr('stroke', vector.isQueryVector ? '#a081d9' : '#000')
            .attr('stroke-width', 2)
            .attr('fill-opacity', vector.isQueryVector ? 0.3 : 0.1)
            .attr('stroke-opacity', 0.8);
        
        // Add hover effects
        polygon.on('mouseover', function() {
            d3.select(this).attr('fill-opacity', 0.5);
            showVectorDetails(null, vector);
        })
        .on('mouseout', function() {
            d3.select(this).attr('fill-opacity', vector.isQueryVector ? 0.3 : 0.1);
        });
        
        // Add vector label if it's query vector or highlighted
        if (vector.isQueryVector || vector.isHighlighted) {
            const centroid = calculatePolygonCentroid(points);
            svg.append('text')
                .attr('x', centroid[0])
                .attr('y', centroid[1])
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .attr('font-size', '10px')
                .attr('fill', vector.isQueryVector ? '#a081d9' : '#22bb11')
                .text(vector.text.substring(0, 15));
        }
    });
}

// Calculate centroid of polygon
function calculatePolygonCentroid(points) {
    const x = points.reduce((sum, p) => sum + p[0], 0) / points.length;
    const y = points.reduce((sum, p) => sum + p[1], 0) / points.length;
    return [x, y];
}

// Update the 3D visualization
function updateVisualization() {
    // If we're in radar chart mode, don't update 3D
    if (currentDimension !== 3) {
        return;
    }
    
    // Calculate data bounds first
    calculateDataBounds();
    
    // Update bounding cube based on new data bounds
    updateBoundingCube();
    
    // Clear existing points and labels
    points.forEach(point => {
        scene.remove(point);
    });
    points = [];
    
    labels.forEach(label => {
        scene.remove(label);
    });
    labels = [];
    
    pointMeshes = []; // Clear point meshes array
    
    // Create 3D points for each vector
    const allVectors = [...vectors];
    if (currentQueryVector) {
        allVectors.push(currentQueryVector);
    }
    
    allVectors.forEach((vector, index) => {
        // Create geometry for the point
        const geometry = new THREE.SphereGeometry(0.08, 8, 8);
        
        // Create material
        const material = new THREE.MeshLambertMaterial({ 
            color: 0x000000, // Always black
            transparent: true,
            opacity: 0.8
        });
        
        // Create mesh
        const point = new THREE.Mesh(geometry, material);
        
        // Set position using vector coordinates (normalized to -1 to 1 range based on actual data bounds)
        const x = normalizeValue(vector.x, 'x');
        const y = normalizeValue(vector.y, 'y');
        const z = normalizeValue(vector.z, 'z');
        point.position.set(x, y, z);
        
        // Store vector data for interaction
        point.userData = {
            vector: vector,
            index: index
        };
        
        // Add to scene and arrays
        scene.add(point);
        points.push(point);
        pointMeshes.push(point); // Add to pointMeshes for raycaster
        
        // Add glow for highlighted points
        if (vector.isHighlighted) {
            const glowSize = vector.isQueryVector ? 0.25 : 0.15; // Larger glow for query vector
            const glowGeometry = new THREE.SphereGeometry(glowSize, 8, 8);
            const glowMaterial = new THREE.MeshBasicMaterial({ 
                color: vector.isQueryVector ? 0xa081d9 : 0x22bb11,
                transparent: true, 
                opacity: 0.3
            });
            const glow = new THREE.Mesh(glowGeometry, glowMaterial);
            glow.position.set(x, y, z);
            scene.add(glow);
            points.push(glow); // Add to points array so it gets cleared on update
        }
        
        // Add text label (only for first 10 points to avoid clutter, or for query vector, or highlighted points)
        if (index < 10 || vector.isQueryVector || vector.isHighlighted) {
            addTextLabel(vector, x, y, z);
        }
    });
    
    // Add raycaster for mouse and touch interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let lastIntersectedPoint = null;
    let touchTimeout = null;
    
    // Add mouse event listeners (desktop)
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('click', onMouseClick);
    
    // Add touch event listeners (mobile)
    renderer.domElement.addEventListener('touchstart', onTouchStart, { passive: false });
    renderer.domElement.addEventListener('touchmove', onTouchMove, { passive: false });
    renderer.domElement.addEventListener('touchend', onTouchEnd, { passive: false });
    
    function onMouseMove(event) {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(pointMeshes);
        
        if (intersects.length > 0) {
            const point = intersects[0].object;
            const vector = point.userData.vector;
            lastIntersectedPoint = point;
            showVectorDetails(event, vector);
        } else {
            lastIntersectedPoint = null;
        }
    }
    
    function onMouseClick(event) {
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(pointMeshes);
        
        if (intersects.length > 0) {
            const point = intersects[0].object;
            const vector = point.userData.vector;
            // Handle click if needed
        }
    }
    
    function onTouchStart(event) {
        event.preventDefault();
        
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
            
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(pointMeshes);
            
            if (intersects.length > 0) {
                const point = intersects[0].object;
                const vector = point.userData.vector;
                lastIntersectedPoint = point;
                
                // Show details immediately on touch
                showVectorDetails(event, vector);
            }
        }
    }
    
    function onTouchMove(event) {
        event.preventDefault();
        
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
            
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(pointMeshes);
            
            if (intersects.length > 0) {
                const point = intersects[0].object;
                const vector = point.userData.vector;
                
                if (lastIntersectedPoint !== point) {
                    lastIntersectedPoint = point;
                    showVectorDetails(event, vector);
                    
                    // Reset timeout
                    if (touchTimeout) {
                        clearTimeout(touchTimeout);
                    }
                    touchTimeout = setTimeout(() => {
                        if (lastIntersectedPoint === point) {
                            document.getElementById('vectorDetails').innerHTML = '';
                            lastIntersectedPoint = null;
                        }
                    }, 3000);
                }
            } else {
                lastIntersectedPoint = null;
            }
        }
    }
    
    function onTouchEnd(event) {
        event.preventDefault();
        // Keep the details visible for a moment after touch ends
        // The timeout will handle clearing them
    }
}



// Show vector details in panel on hover/touch
function showVectorDetails(event, d) {
    const container = document.getElementById('vectorDetails');
    
    if (!d) {
        container.innerHTML = '';
        return;
    }
    
    const vectorStr = d.vector ? d.vector.map(v => v.toFixed(4)).join(', ') : 'N/A';
    const deleteLink = d.isQueryVector ? '' : `<a href="javascript:void(0)" onclick="initiateDeleteVector('${d.id}')" class="vector-delete-link">delete</a>`;
    
    container.innerHTML = `
        <div class="vector-detail-item">
            <div class="vector-detail-content">
                <strong>text:</strong> ${d.text}<br>
                <strong>vector:</strong> [${vectorStr}]
            </div>
            ${deleteLink}
        </div>
    `;
}

// Delete vector from database
async function deleteVector(vectorId) {
    try {
        const response = await fetch(`${API_BASE}/vectors/${vectorId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove from local arrays
            vectors = vectors.filter(v => v.id !== vectorId);
            highlightedPoints.delete(vectorId);
            
            // Clear vector details panel
            document.getElementById('vectorDetails').innerHTML = '';
            
            // Update visualization
            updateVisualization();
            
            // Update stats
            await loadStats();
            
            console.log('Vector deleted successfully');
        } else {
            console.error('Failed to delete vector:', data.error);
        }
    } catch (error) {
        console.error('Error deleting vector:', error);
    }
}

// Initiate delete with countdown confirmation
function initiateDeleteVector(vectorId) {
    // Find the delete link element
    const deleteLink = document.querySelector(`a[onclick="initiateDeleteVector('${vectorId}')"]`);
    if (!deleteLink) return;
    
    // Prevent default link behavior
    event.preventDefault();
    
    // Store original text to restore if cancelled
    const originalText = deleteLink.textContent;
    const originalOnClick = deleteLink.onclick;
    
    // Start countdown
    let countdown = 5;
    
    // Update link text and onclick
    deleteLink.textContent = `cancel (${countdown}s)`;
    deleteLink.onclick = function(e) {
        e.preventDefault();
        // Cancel the deletion
        deleteLink.textContent = originalText;
        deleteLink.onclick = originalOnClick;
        clearInterval(countdownInterval);
    };
    
    // Countdown timer
    const countdownInterval = setInterval(() => {
        countdown--;
        if (countdown > 0) {
            deleteLink.textContent = `cancel (${countdown}s)`;
        } else {
            // Time's up, execute deletion
            deleteLink.textContent = `cancel (0s)`;
            clearInterval(countdownInterval);
            
            // Execute delete after a brief moment
            setTimeout(() => {
                deleteVector(vectorId);
            }, 100);
        }
    }, 1000);
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
                x: data.vector[0], // Use raw vector values directly
                y: data.vector[1],
                z: data.vector[2],
                vector: data.vector,
                text: text,
                type: 'document',
                timestamp: new Date().toISOString(),
                metadata: data.metadata || {},
                isHighlighted: false
            };
            
            vectors.push(newVector);
            
            // Highlight the newly added vector before updating visualization
            newVector.isHighlighted = true;
            highlightedPoints.add(newVector.id);
            
            // Update visualization based on current mode
            if (currentDimension === 3) {
                updateVisualization();
            } else {
                showRadarChart();
            }
            
            // Update stats
            await loadStats();
            

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
        highlightedPoints.clear();
        vectors.forEach(vector => {
            vector.isHighlighted = false;
        });
        
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
            x: embeddingData.embedding[0], // Use raw vector values directly
            y: embeddingData.embedding[1],
            z: embeddingData.embedding[2],
            vector: embeddingData.embedding,
            text: query,
            isQueryVector: true,
            isHighlighted: true // Highlight the query vector
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
        
        // Show search term vector details
        showVectorDetails(null, currentQueryVector);
        
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
            highlightedPoints.add(vector.id);
        }
    });
    
    // Update visualization based on current mode
    if (currentDimension === 3) {
        updateVisualization();
    } else {
        showRadarChart();
    }
}

// Highlight a specific vector
function highlightVector(vectorId) {
    const vector = vectors.find(v => v.id === vectorId);
    if (!vector) return;
    
    // Add to highlighted set
    highlightedPoints.add(vectorId);
    vector.isHighlighted = true;
    
    // Update visualization to show highlighting
    updateVisualization();
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
    
    // Update query summary container
    const querySummaryContainer = document.getElementById('querySummary');
    querySummaryContainer.innerHTML = querySummary;
    
    // Update results container
    container.innerHTML = resultsHtml;
}

// Clear search
function clearSearch() {
    searchResults = [];
    currentQueryVector = null;
    
    // Clear all highlights
    highlightedPoints.clear();
    
    // Reset vectors
    vectors.forEach(vector => {
        vector.isSearchResult = false;
        vector.isQueryVector = false;
        vector.isHighlighted = false;
    });
    
    // Update visualization based on current mode
    if (currentDimension === 3) {
        updateVisualization();
    } else {
        showRadarChart();
    }
    
    // Clear displays
    document.getElementById('searchResults').innerHTML = '...';
    document.getElementById('querySummary').innerHTML = '';
    document.getElementById('searchQuery').value = '';
    document.getElementById('vectorDetails').innerHTML = '';
    
    // Reset the search results title
    const resultsSection = document.getElementById('searchResults').closest('.results-section');
    const titleElement = resultsSection.querySelector('h3');
    titleElement.textContent = 'Search Results';
}

// Reset view
function resetView() {
    // Reset camera position - see comments above for adjustment guide
    // Quick adjustments:
    // - More zoom: decrease all values (e.g., 2.0, -1.8, 1.0)
    // - Less zoom: increase all values (e.g., 3.0, -2.6, 1.6)
    // - Rotate left: decrease X, increase Z
    // - Rotate right: increase X, decrease Z
    // - Look more up: decrease Y (more negative)
    // - Look more down: increase Y (less negative)
    camera.position.set(DEFAULT_CAMERA_POSITION[0], DEFAULT_CAMERA_POSITION[1], DEFAULT_CAMERA_POSITION[2]);
    controls.reset();
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
                <span class="stat-label">Model:</span>
                <span class="stat-value">${data.vector_db.model_name}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Original Dim:</span>
                <span class="stat-value">${data.vector_db.original_dimension}D</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Reduced Dim:</span>
                <span class="stat-value">${data.vector_db.dimension}D</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">PCA Status:</span>
                <span class="stat-value">${data.vector_db.pca_fitted ? 'Fitted' : 'Not Fitted'}</span>
            </div>
        `;
        
        document.getElementById('stats').innerHTML = statsHtml;
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stats').innerHTML = '<div>Failed to load stats</div>';
    }
}

// Utility functions 