// script.js yang akan diletakkan di static/js/script.js

// Utility function untuk toggle loading state
const toggleLoading = (formId, isLoading) => {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const submitButton = form.querySelector('button[type="submit"]');
    const formContent = form.querySelector('.form-content');
    
    if (isLoading) {
        // Add loading overlay
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        loadingOverlay.innerHTML = `
            <div class="bg-white p-4 rounded-lg shadow-lg">
                <div class="flex items-center space-x-3">
                    <div class="w-3 h-3 bg-blue-500 rounded-full animate-bounce"></div>
                    <div class="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                    <div class="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
                <div class="text-gray-700 mt-2">Processing...</div>
            </div>
        `;
        document.body.appendChild(loadingOverlay);
        
        submitButton.disabled = true;
        submitButton.classList.add('opacity-50', 'cursor-not-allowed');
        if (formContent) {
            formContent.classList.add('opacity-50');
        }
    } else {
        // Remove loading overlay
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
        
        submitButton.disabled = false;
        submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
        if (formContent) {
            formContent.classList.remove('opacity-50');
        }
    }
};

// Utility function untuk menampilkan pesan
const showMessage = (elementId, message, type = 'info') => {
    const element = document.getElementById(elementId);
    if (!element) return;

    const classes = {
        success: 'bg-green-100 text-green-800 border-green-400',
        error: 'bg-red-100 text-red-800 border-red-400',
        info: 'bg-blue-100 text-blue-800 border-blue-400'
    };

    element.innerHTML = `
        <div class="p-4 rounded-lg ${classes[type]} border">
            <p class="text-sm">${message}</p>
        </div>
    `;
};

// File preview functionality
const setupFilePreview = (inputId, previewContainerId) => {
    const input = document.getElementById(inputId);
    const container = document.getElementById(previewContainerId);
    
    if (!input || !container) return;

    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        
        // Reset container
        container.innerHTML = '';
        
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                container.innerHTML = `
                    <div class="mt-4 relative">
                        <img src="${e.target.result}" 
                             alt="Preview" 
                             class="w-full h-48 object-cover rounded-lg shadow-md">
                        <button type="button" 
                                class="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                                onclick="clearFileInput('${inputId}', '${previewContainerId}')">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        }
    });
};

// Clear file input
const clearFileInput = (inputId, previewContainerId) => {
    const input = document.getElementById(inputId);
    const container = document.getElementById(previewContainerId);
    if (input) input.value = '';
    if (container) container.innerHTML = '';
};

// Handle upload face
document.getElementById('uploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const nameInput = document.getElementById('name');
    const fileInput = document.getElementById('file');
    
    if (!nameInput?.value.trim()) {
        showMessage('uploadMessage', 'Please enter a name', 'error');
        return;
    }
    
    if (!fileInput?.files[0]) {
        showMessage('uploadMessage', 'Please select an image', 'error');
        return;
    }
    
    toggleLoading('uploadForm', true);
    
    try {
        const formData = new FormData();
        formData.append('name', nameInput.value.trim());
        formData.append('file', fileInput.files[0]);
        
        const response = await fetch('/add_known_face', {
            method: 'POST',
            body: formData,
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showMessage('uploadMessage', result.message, 'success');
            document.getElementById('uploadForm').reset();
            document.getElementById('uploadPreviewContainer').innerHTML = '';
        } else {
            showMessage('uploadMessage', result.error, 'error');
        }
    } catch (error) {
        showMessage('uploadMessage', 'An error occurred. Please try again.', 'error');
    } finally {
        toggleLoading('uploadForm', false);
    }
});

// Handle search face
document.getElementById('searchForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fileInput = document.getElementById('searchFile');
    if (!fileInput?.files[0]) {
        showMessage('searchResults', 'Please select an image', 'error');
        return;
    }
    
    toggleLoading('searchForm', true);
    
    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        const response = await fetch('/find_face', {
            method: 'POST',
            body: formData,
        });
        
        const result = await response.json();
        const resultsDiv = document.getElementById('searchResults');
        
        if (response.ok && result.match) {
            resultsDiv.innerHTML = `
                <div class="mt-6">
                    <h3 class="text-lg font-semibold mb-4">Found ${result.matches.length} match${result.matches.length > 1 ? 'es' : ''}</h3>
                    <div class="space-y-4">
                        ${result.matches.map(match => `
                            <div class="bg-white rounded-lg shadow-md p-4 flex items-center space-x-4">
                                <img src="static/images_upload/${match.file_name}" 
                                     alt="${match.name}" 
                                     class="w-16 h-16 rounded-full object-cover">
                                <div class="flex-1">
                                    <h4 class="font-semibold text-lg">${match.name}</h4>
                                    <div class="flex items-center mt-2">
                                        <div class="flex-1 bg-gray-200 rounded-full h-2">
                                            <div class="bg-blue-600 rounded-full h-2" 
                                                 style="width: ${match.similarity_score * 100}%"></div>
                                        </div>
                                        <span class="ml-2 text-sm text-gray-600">
                                            ${(match.similarity_score * 100).toFixed(1)}%
                                        </span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else {
            showMessage('searchResults', result.message || 'No matching faces found.', 'info');
        }
    } catch (error) {
        showMessage('searchResults', 'An error occurred. Please try again.', 'error');
    } finally {
        toggleLoading('searchForm', false);
    }
});

// Initialize file previews
document.addEventListener('DOMContentLoaded', () => {
    setupFilePreview('file', 'uploadPreviewContainer');
    setupFilePreview('searchFile', 'searchPreviewContainer');
});