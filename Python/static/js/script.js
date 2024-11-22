// Global state for search
let currentSearchState = {
    formData: null,
    currentPage: 1
};

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
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
        if (formContent) {
            formContent.classList.add('opacity-50');
        }
    } else {
        // Remove loading overlay
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
        
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
        }
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
            // Validate file type
            const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
            if (!validTypes.includes(file.type)) {
                showMessage(previewContainerId, 'Please select a valid image file (JPEG, JPG, or PNG)', 'error');
                input.value = '';
                return;
            }

            // Validate file size (max 5MB)
            const maxSize = 5 * 1024 * 1024; // 5MB in bytes
            if (file.size > maxSize) {
                showMessage(previewContainerId, 'File size should not exceed 5MB', 'error');
                input.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                container.innerHTML = `
                    <div class="mt-4 relative">
                        <img src="${e.target.result}" 
                             alt="Preview" 
                             class="w-full h-48 object-cover rounded-lg shadow-md">
                        <button type="button" 
                                class="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition duration-200"
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

// Render pagination controls
const renderPagination = (pagination, containerId) => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const { current_page, total_pages, has_next, has_prev } = pagination;
    
    // Don't show pagination if only one page
    if (total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    // Create pagination buttons
    const buttons = [];
    
    // Previous button
    buttons.push(`
        <button 
            class="px-3 py-1 rounded-md ${has_prev 
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'}"
            ${!has_prev ? 'disabled' : ''}
            onclick="changePage(${current_page - 1})"
        >
            Previous
        </button>
    `);

    // Page numbers
    for (let i = 1; i <= total_pages; i++) {
        if (
            i === 1 || // First page
            i === total_pages || // Last page
            (i >= current_page - 1 && i <= current_page + 1) // Pages around current
        ) {
            buttons.push(`
                <button 
                    class="px-3 py-1 rounded-md ${i === current_page 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-blue-100 text-blue-700 hover:bg-blue-200'}"
                    onclick="changePage(${i})"
                >
                    ${i}
                </button>
            `);
        } else if (
            i === current_page - 2 ||
            i === current_page + 2
        ) {
            buttons.push(`<span class="px-2">...</span>`);
        }
    }

    // Next button
    buttons.push(`
        <button 
            class="px-3 py-1 rounded-md ${has_next 
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'}"
            ${!has_next ? 'disabled' : ''}
            onclick="changePage(${current_page + 1})"
        >
            Next
        </button>
    `);

    // Render pagination
    container.innerHTML = `
        <div class="flex items-center justify-center space-x-2 mt-4">
            ${buttons.join('')}
        </div>
    `;
};

// Render search results
const renderSearchResults = (results) => {
    const resultsDiv = document.getElementById('searchResults');
    if (!resultsDiv) return;

    if (results.match) {
        resultsDiv.innerHTML = `
            <div class="mt-6">
                <h3 class="text-lg font-semibold mb-4">
                    Found ${results.pagination.total_items} match${results.pagination.total_items > 1 ? 'es' : ''}
                    (Showing page ${results.pagination.current_page} of ${results.pagination.total_pages})
                </h3>
                <div class="space-y-4">
                    ${results.matches.map(match => `
                        <div class="bg-white rounded-lg shadow-md p-4 flex items-center space-x-4 hover:shadow-lg transition-shadow duration-300">
                            <img src="/static/images_upload/${match.file_name}" 
                                 alt="${match.name}" 
                                 class="w-16 h-16 rounded-full object-cover border-2 border-blue-500">
                            <div class="flex-1">
                                <h4 class="font-semibold text-lg text-gray-900">${match.name}</h4>
                                <div class="flex items-center mt-2">
                                    <div class="flex-1 bg-gray-200 rounded-full h-2">
                                        <div class="bg-blue-600 rounded-full h-2 transition-all duration-500" 
                                             style="width: ${match.similarity_score * 100}%"></div>
                                    </div>
                                    <span class="ml-2 text-sm text-gray-600 font-medium">
                                        ${(match.similarity_score * 100).toFixed(1)}%
                                    </span>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div id="paginationControls" class="mt-6"></div>
            </div>
        `;

        // Render pagination controls
        renderPagination(results.pagination, 'paginationControls');
    } else {
        showMessage('searchResults', results.message || 'No matching faces found.', 'info');
    }
};

// Change page function
const changePage = async (page) => {
    if (!currentSearchState.formData) return;
    
    currentSearchState.currentPage = page;
    await performSearch(currentSearchState.formData, page);
};

// Perform search function
const performSearch = async (formData, page = 1) => {
    toggleLoading('searchForm', true);
    
    try {
        // Clone formData and append page number
        const searchData = new FormData();
        for (let [key, value] of formData.entries()) {
            searchData.append(key, value);
        }
        searchData.append('page', page);
        
        const response = await fetch('/find_face', {
            method: 'POST',
            body: searchData,
        });
        
        const result = await response.json();
        
        if (response.ok) {
            renderSearchResults(result);
        } else {
            showMessage('searchResults', result.error, 'error');
        }
    } catch (error) {
        showMessage('searchResults', 'An error occurred. Please try again.', 'error');
    } finally {
        toggleLoading('searchForm', false);
    }
};

// Handle upload face
document.getElementById('uploadForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const nameInput = document.getElementById('name');
    const fileInput = document.getElementById('file');
    
    // Form validation
    if (!nameInput?.value.trim()) {
        showMessage('uploadMessage', 'Please enter a name', 'error');
        nameInput.focus();
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
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // Save current search state
    currentSearchState.formData = formData;
    currentSearchState.currentPage = 1;
    
    // Perform search
    await performSearch(formData, 1);
});

// Initialize file previews
document.addEventListener('DOMContentLoaded', () => {
    setupFilePreview('file', 'uploadPreviewContainer');
    setupFilePreview('searchFile', 'searchPreviewContainer');
});