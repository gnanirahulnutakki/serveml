// ServeML Frontend Application
const API_URL = 'http://localhost:8000';

// State management
let currentDeploymentId = null;
let pollInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadDeployments();
    
    // Set up form submission
    const deployForm = document.getElementById('deploy-form');
    deployForm.addEventListener('submit', handleDeploy);
});

// Handle model deployment
async function handleDeploy(event) {
    event.preventDefault();
    
    const modelName = document.getElementById('model-name').value;
    const modelFile = document.getElementById('model-file').files[0];
    const requirementsFile = document.getElementById('requirements-file').files[0];
    
    if (!modelFile || !requirementsFile) {
        showToast('Please select both files', 'error');
        return;
    }
    
    // Validate file sizes (max 100MB for model)
    if (modelFile.size > 100 * 1024 * 1024) {
        showToast('Model file too large (max 100MB)', 'error');
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('model_file', modelFile);
    formData.append('requirements_file', requirementsFile);
    if (modelName) {
        formData.append('name', modelName);
    }
    
    // Disable submit button
    const deployBtn = document.getElementById('deploy-btn');
    deployBtn.disabled = true;
    deployBtn.textContent = 'Deploying...';
    
    try {
        const response = await fetch(`${API_URL}/api/v1/deploy`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Deployment failed');
        }
        
        const deployment = await response.json();
        currentDeploymentId = deployment.id;
        
        // Show success message
        showToast('Deployment started successfully!', 'success');
        
        // Show status section
        showDeploymentStatus(deployment);
        
        // Start polling for status updates
        startPolling(deployment.id);
        
        // Reload deployments list
        loadDeployments();
        
        // Reset form
        document.getElementById('deploy-form').reset();
        
    } catch (error) {
        showToast(error.message, 'error');
        console.error('Deployment error:', error);
    } finally {
        deployBtn.disabled = false;
        deployBtn.textContent = 'Deploy Model';
    }
}

// Show deployment status
function showDeploymentStatus(deployment) {
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('status-section').style.display = 'block';
    
    document.getElementById('deployment-id').textContent = deployment.id;
    document.getElementById('deployment-name').textContent = deployment.name;
    updateStatusBadge(deployment.status);
    
    if (deployment.endpoint_url) {
        document.getElementById('endpoint-item').style.display = 'block';
        document.getElementById('deployment-endpoint').textContent = deployment.endpoint_url;
    }
}

// Update status badge
function updateStatusBadge(status) {
    const statusElement = document.getElementById('deployment-status');
    statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusElement.className = `status-badge ${status}`;
    
    // Update progress bar
    const progressBar = document.getElementById('progress-bar');
    if (status === 'deploying') {
        progressBar.style.display = 'block';
    } else {
        progressBar.style.display = 'none';
    }
}

// Poll for deployment status
function startPolling(deploymentId) {
    // Clear any existing polling
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/api/v1/deployments/${deploymentId}`);
            const deployment = await response.json();
            
            updateStatusBadge(deployment.status);
            
            if (deployment.endpoint_url) {
                document.getElementById('endpoint-item').style.display = 'block';
                document.getElementById('deployment-endpoint').textContent = deployment.endpoint_url;
            }
            
            // Stop polling if deployment is complete
            if (deployment.status === 'active' || deployment.status === 'failed') {
                clearInterval(pollInterval);
                pollInterval = null;
                
                if (deployment.status === 'active') {
                    showToast('Deployment completed successfully!', 'success');
                } else {
                    showToast('Deployment failed', 'error');
                }
                
                loadDeployments();
            }
        } catch (error) {
            console.error('Polling error:', error);
        }
    }, 5000); // Poll every 5 seconds
}

// Load deployments list
async function loadDeployments() {
    try {
        const response = await fetch(`${API_URL}/api/v1/deployments`);
        const data = await response.json();
        
        const deploymentsList = document.getElementById('deployments-list');
        
        if (data.total === 0) {
            deploymentsList.innerHTML = '<p class="empty-state">No deployments yet. Deploy your first model above!</p>';
            return;
        }
        
        deploymentsList.innerHTML = data.deployments.map(deployment => `
            <div class="deployment-item">
                <div class="deployment-info">
                    <h3>${deployment.name}</h3>
                    <div class="deployment-meta">
                        <span>Status: <span class="status-badge ${deployment.status}">${deployment.status}</span></span>
                        <span> • Created: ${formatDate(deployment.created_at)}</span>
                    </div>
                    ${deployment.endpoint_url ? `<div class="deployment-meta">Endpoint: ${deployment.endpoint_url}</div>` : ''}
                </div>
                <div class="deployment-actions">
                    ${deployment.status === 'active' ? `<button class="btn btn-primary btn-small" onclick="testModel('${deployment.id}')">Test</button>` : ''}
                    <button class="btn btn-secondary btn-small" onclick="deleteDeployment('${deployment.id}')">Delete</button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading deployments:', error);
        showToast('Failed to load deployments', 'error');
    }
}

// Delete deployment
async function deleteDeployment(deploymentId) {
    if (!confirm('Are you sure you want to delete this deployment?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/v1/deployments/${deploymentId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete deployment');
        }
        
        showToast('Deployment deleted successfully', 'success');
        loadDeployments();
        
        // If we're currently viewing this deployment, reset the form
        if (currentDeploymentId === deploymentId) {
            resetForm();
        }
        
    } catch (error) {
        console.error('Delete error:', error);
        showToast('Failed to delete deployment', 'error');
    }
}

// Test model
async function testModel(deploymentId) {
    // Get deployment details first
    try {
        const response = await fetch(`${API_URL}/api/v1/deployments/${deploymentId}`);
        const deployment = await response.json();
        
        if (!deployment.model_metadata) {
            showToast('Model metadata not available', 'error');
            return;
        }
        
        // Generate test data based on model metadata
        let testData = {};
        if (deployment.model_metadata.input_shape) {
            const inputSize = deployment.model_metadata.input_shape[0] || 4;
            testData = {
                data: Array(inputSize).fill(0).map(() => Math.random())
            };
        } else {
            // Default test data
            testData = {
                data: [5.1, 3.5, 1.4, 0.2]  // Iris dataset sample
            };
        }
        
        // Show loading
        showToast('Testing model...', 'info');
        
        // Call test endpoint
        const testResponse = await fetch(`${API_URL}/api/v1/test-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                deployment_id: deploymentId,
                data: testData.data
            })
        });
        
        if (!testResponse.ok) {
            throw new Error('Test failed');
        }
        
        const result = await testResponse.json();
        
        // Show result in a nice format
        const resultMessage = `
Prediction: ${JSON.stringify(result.output.prediction)}
Model Type: ${result.output.model_type}
${result.output.probability ? `Confidence: ${JSON.stringify(result.output.probability)}` : ''}
        `.trim();
        
        alert(resultMessage);
        
    } catch (error) {
        showToast('Model test failed: ' + error.message, 'error');
    }
}

// Reset form and show upload section
function resetForm() {
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('status-section').style.display = 'none';
    document.getElementById('deploy-form').reset();
    
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    
    currentDeploymentId = null;
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Format date
function formatDate(isoDate) {
    const date = new Date(isoDate);
    const now = new Date();
    const diff = now - date;
    
    // If less than 1 minute
    if (diff < 60000) {
        return 'Just now';
    }
    
    // If less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    }
    
    // If less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    }
    
    // Otherwise show date
    return date.toLocaleDateString();
}