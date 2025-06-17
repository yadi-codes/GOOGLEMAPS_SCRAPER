// Global variables
let allPlaces = [];
let filteredPlaces = [];
let categories = [];

// DOM elements
const searchInput = document.getElementById('searchInput');
console.log(searchInput);
const categoryFilter = document.getElementById('categoryFilter');
const ratingFilter = document.getElementById('ratingFilter');
const refreshBtn = document.getElementById('refreshBtn');
const exportCsvBtn = document.getElementById('exportCsvBtn');
const exportPdfBtn = document.getElementById('exportPdfBtn');
const tableBody = document.getElementById('tableBody');
const tableDescription = document.getElementById('tableDescription');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // loadSampleData(); // Load sample data for demo
    loadRealData();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    searchInput.addEventListener('input', debounce(filterData, 300));
    categoryFilter.addEventListener('change', filterData);
    ratingFilter.addEventListener('change', filterData);
    // refreshBtn.addEventListener('click', loadSampleData);
    refreshBtn.addEventListener('click', loadRealData);
    exportCsvBtn.addEventListener('click', () => exportData('csv'));
    exportPdfBtn.addEventListener('click', () => exportData('pdf'));
}

// Debounce function for search input
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function loadRealData() {
    showLoading();

    fetch('http://127.0.0.1:5000/api/places')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch data');
            }
            return response.json();
        })
        .then(data => {
            allPlaces = data.places.map(place => {
                let cleanedRating = parseFloat(place.rating);

                // If parseFloat fails (NaN), default to 0
                if (isNaN(cleanedRating)) {
                    cleanedRating = 0;
                }

                return {
                    ...place,
                    rating: cleanedRating
                };
            });

            // Extract unique categories
            // categories = [...new Set(allPlaces.flatMap(place => place.categories))].sort();

            populateCategoryFilter();
            updateStats();
            filterData();
            hideLoading();

            showToast('Data loaded successfully', 'success');
        })
        .catch(error => {
            console.error('Error loading data:', error);
            showToast('Error loading data', 'error');
            hideLoading();
        });
}

// Show loading state
function showLoading() {
    tableBody.innerHTML = `
        <tr class="loading-row">
            <td colspan="7">
                <div class="loading-container">
                    <div class="spinner"></div>
                    <span>Loading data...</span>
                </div>
            </td>
        </tr>
    `;
    tableDescription.textContent = 'Loading data...';
}

// Hide loading state
function hideLoading() {
    // Loading will be replaced by actual data
}

// Populate category filter dropdown
function populateCategoryFilter() {
    // Step 1: Create a Set to store unique categories
    const categoriesSet = new Set();

    // Step 2: Loop through all places to collect categories
    allPlaces.forEach(place => {
        // Check if place.categories exists and is an array
        if (place.categories && Array.isArray(place.categories)) {
            // Loop through each category in the place
            place.categories.forEach(category => {
                if (category) { // Skip if category is null or undefined
                    categoriesSet.add(category.trim()); // Add category to Set
                }
            });
        }
    });

    // Step 3: Convert the Set to an Array (Sets cannot be looped with forEach directly)
    const uniqueCategories = Array.from(categoriesSet);

    // Step 4: Clear the existing options and add "All Categories" option
    categoryFilter.innerHTML = '<option value="all">All Categories</option>';

    // Step 5: Add each unique category as an option to the dropdown
    uniqueCategories.forEach(category => {
        const option = document.createElement('option'); // Create an option element
        option.value = category; // Set the value (what will be used in filtering)
        option.textContent = category; // Set the visible text in the dropdown
        categoryFilter.appendChild(option); // Add the option to the dropdown
    });
}

// Update statistics
function updateStats() {
    const totalPlaces = allPlaces.length;

    // Calculate unique categories
    const categoriesSet = new Set();
    allPlaces.forEach(place => {
        if (place.categories && Array.isArray(place.categories)) {
            place.categories.forEach(category => {
                if (category) {
                    categoriesSet.add(category.trim());
                }
            });
        }
    });
    const totalCategories = categoriesSet.size;

    // Calculate average rating (no need to filter now)
    const validRatings = allPlaces.filter(place => place.rating > 0);
    const avgRating = validRatings.length > 0
        ? (validRatings.reduce((sum, place) => sum + place.rating, 0) / validRatings.length).toFixed(1)
        : '0.0';

    document.getElementById('totalPlaces').textContent = totalPlaces.toLocaleString();
    document.getElementById('totalCategories').textContent = totalCategories;
    document.getElementById('avgRating').textContent = avgRating;
}

// Filter data based on search and filters
function filterData() {
    const searchTerm = searchInput.value.toLowerCase();
    const categoryValue = categoryFilter.value;
    const ratingValue = ratingFilter.value;

    filteredPlaces = allPlaces.filter(place => {
        // Search filter
        const matchesSearch = !searchTerm || 
            place.name?.toLowerCase().includes(searchTerm) ||
            place.address?.toLowerCase().includes(searchTerm) ||
            place.categories?.some(cat => cat.toLowerCase().includes(searchTerm));

        // Category filter
        const matchesCategory = categoryValue === 'all' || 
            place.categories.includes(categoryValue);

        // Rating filter
        const matchesRating = ratingValue === 'all' || 
            place.rating >= parseFloat(ratingValue);

        return matchesSearch && matchesCategory && matchesRating;
    });

    updateFilteredCount();
    renderTable();
}

// Update filtered count
function updateFilteredCount() {
    document.getElementById('filteredCount').textContent = filteredPlaces.length.toLocaleString();
    tableDescription.textContent = `Showing ${filteredPlaces.length} of ${allPlaces.length} places`;
}

// Render the data table
function renderTable() {
    if (filteredPlaces.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="fas fa-search"></i>
                    <div>No data found matching your filters</div>
                </td>
            </tr>
        `;
        return;
    }

    tableBody.innerHTML = filteredPlaces.map(place => `
        <tr>
            <td>
                <div class="cell-name" title="${escapeHtml(place.name)}">
                    ${escapeHtml(place.name)}
                </div>
            </td>
            <td>
                <div class="cell-address" title="${escapeHtml(place.address)}">
                    ${escapeHtml(place.address || 'N/A')}
                </div>
            </td>
            <td>${escapeHtml(place.phone || 'N/A')}</td>
            <td>
                <div class="cell-rating">
                    <span>${place.rating}</span>
                    <i class="fas fa-star rating-star"></i>
                </div>
            </td>
            <td>${place.review_count?.toLocaleString() || '0'}</td>
            <td>
                <div class="cell-categories">
                    ${place.categories.slice(0, 2).map(cat => 
                        `<span class="category-badge">${escapeHtml(cat)}</span>`
                    ).join('')}
                    ${place.categories.length > 2 ? 
                        `<span class="category-badge more">+${place.categories.length - 2}</span>` : ''
                    }
                </div>
            </td>
            <td class="cell-date">${formatDate(place.scraped_at)}</td>
        </tr>
    `).join('');
}

// Format date
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export data
function exportData(format) {
    if (filteredPlaces.length === 0) {
        showToast('No data to export', 'error');
        return;
    }

    const button = format === 'csv' ? exportCsvBtn : exportPdfBtn;
    button.disabled = true;
    button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Exporting...`;

    setTimeout(() => {
        try {
            if (format === 'csv') {
                exportCSV();
            } else if (format === 'pdf') {
                exportPDF();
            }
            showToast(`Data exported as ${format.toUpperCase()} successfully`, 'success');
        } catch (error) {
            showToast('Export failed', 'error');
            console.error('Export error:', error);
        } finally {
            button.disabled = false;
            button.innerHTML = format === 'csv' 
                ? '<i class="fas fa-download"></i> CSV'
                : '<i class="fas fa-file-pdf"></i> PDF';
        }
    }, 500);
}

// Export as CSV
function exportCSV() {
    const headers = [
        'Name', 'Address', 'Phone', 'Rating', 'Review Count', 
        'Categories', 'Scraped Date', 'Latitude', 'Longitude'
    ];

    const csvContent = [
        headers.join(','),
        ...filteredPlaces.map(place => [
            `"${place.name.replace(/"/g, '""')}"`,
            `"${(place.address || '').replace(/"/g, '""')}"`,
            `"${place.phone || ''}"`,
            place.rating || '',
            place.review_count || '',
            `"${place.categories.join('; ')}"`,
            formatDate(place.scraped_at),
            place.latitude || '',
            place.longitude || ''
        ].join(','))
    ].join('\n');

    downloadFile(csvContent, 'places-data.csv', 'text/csv');
}

// Export as PDF
function exportPDF() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Title
    doc.setFontSize(20);
    doc.text('Google Maps Business Data', 20, 20);

    // Filters info
    doc.setFontSize(12);
    let yPos = 35;
    
    const searchTerm = searchInput.value;
    const categoryValue = categoryFilter.value;
    const ratingValue = ratingFilter.value;

    if (searchTerm) {
        doc.text(`Search: ${searchTerm}`, 20, yPos);
        yPos += 7;
    }
    if (categoryValue !== 'all') {
        doc.text(`Category: ${categoryValue}`, 20, yPos);
        yPos += 7;
    }
    if (ratingValue !== 'all') {
        doc.text(`Min Rating: ${ratingValue}`, 20, yPos);
        yPos += 7;
    }

    doc.text(`Total Records: ${filteredPlaces.length}`, 20, yPos);
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, 20, yPos + 7);

    // Table
    const tableData = filteredPlaces.map(place => [
        place.name,
        place.address || 'N/A',
        place.phone || 'N/A',
        place.rating?.toString() || 'N/A',
        place.review_count?.toString() || '0',
        place.categories.join(', '),
        formatDate(place.scraped_at)
    ]);

    doc.autoTable({
        head: [['Name', 'Address', 'Phone', 'Rating', 'Reviews', 'Categories', 'Scraped']],
        body: tableData,
        startY: yPos + 15,
        styles: { fontSize: 8 },
        columnStyles: {
            0: { cellWidth: 25 },
            1: { cellWidth: 35 },
            2: { cellWidth: 20 },
            3: { cellWidth: 15 },
            4: { cellWidth: 15 },
            5: { cellWidth: 30 },
            6: { cellWidth: 20 }
        }
    });

    doc.save('places-data.pdf');
}

// Download file
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const icon = toast.querySelector('.toast-icon');
    const messageEl = toast.querySelector('.toast-message');

    // Set content
    messageEl.textContent = message;
    
    // Set icon and class
    toast.className = `toast ${type}`;
    if (type === 'success') {
        icon.className = 'toast-icon fas fa-check-circle';
    } else if (type === 'error') {
        icon.className = 'toast-icon fas fa-exclamation-circle';
    }

    // Show toast
    toast.classList.add('show');

    // Hide after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// API Integration (replace sample data with actual MySQL data)
async function fetchDataFromAPI() {
    try {
        const response = await fetch('/api/places'); // Your backend endpoint
        if (!response.ok) throw new Error('Failed to fetch data');
        
        const data = await response.json();
        allPlaces = data.places;
        categories = data.categories;
        
        populateCategoryFilter();
        updateStats();
        filterData();
        
        showToast('Data loaded successfully', 'success');
    } catch (error) {
        showToast('Failed to fetch data from database', 'error');
        console.error('API Error:', error);
    }
}