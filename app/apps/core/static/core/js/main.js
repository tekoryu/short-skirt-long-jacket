/**
 * Main JavaScript for SEAF Digital
 * Using Alpine.js for reactivity and HTMX for dynamic content
 */

// Helper function to show toast notifications
window.showNotification = function(message, type = 'info') {
    window.dispatchEvent(new CustomEvent('notify', { 
        detail: { message, type } 
    }));
};

// Dark mode persistence
document.addEventListener('alpine:init', () => {
    // Load dark mode preference from localStorage
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    if (savedDarkMode) {
        document.body.setAttribute('x-data', JSON.stringify({ darkMode: true }));
    }
});

// Save dark mode preference when it changes
document.addEventListener('DOMContentLoaded', function() {
    // Watch for dark mode changes and persist to localStorage
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                const isDark = document.body.classList.contains('dark-mode');
                localStorage.setItem('darkMode', isDark);
            }
        });
    });
    
    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['class']
    });
});

