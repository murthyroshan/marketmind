/**
 * Global App Logic & State Management
 * Handles navigation active states and localStorage persistence.
 */

const STORAGE_KEY = 'salesSparkData_v2';

// Default State
const defaultState = {
    campaigns: 0,
    leadsScored: 0,
    hotLeads: 0,
    totalScore: 0,
    history: [] // Optional: Store actual records if needed later
};

// Global App State
let appState = { ...defaultState };

// --- Persistence ---
function loadState() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        try {
            appState = JSON.parse(saved);
        } catch (e) {
            console.error("Failed to parse saved state", e);
            appState = { ...defaultState };
        }
    }
}

function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
    // Trigger custom event so dashboard can update if needed (though implemented on page load usually)
    window.dispatchEvent(new Event('stateUpdated'));
}

// --- Navigation ---
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
        // Simple check: if href matches filename
        const href = link.getAttribute('href');
        if (currentPath.includes(href) || (currentPath.endsWith('/') && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadState();
    highlightActiveNav();
});
