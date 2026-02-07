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
    initChatbot();
});

// --- Phase 6: AI Chatbot Injection ---
// --- Phase 6: AI Chatbot Injection ---
function initChatbot() {
    // 1. Inject HTML with Premium Structure
    const chatHTML = `
        <div class="chatbot-widget">
            <button class="chat-toggle-btn" onclick="toggleChat()">
                <span class="chat-icon">🤖</span>
                <span class="chat-pulse"></span>
            </button>
            <div class="chat-window" id="chatWindow">
                <div class="chat-header">
                    <div class="header-info">
                        <h3>SalesSpark AI</h3>
                        <span class="header-subtitle">Your sales intelligence copilot</span>
                    </div>
                    <button class="chat-close-btn" onclick="toggleChat()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <!-- Gradient Divider -->
                <div class="chat-divider"></div>
                
                <div class="chat-body" id="chatBody">
                    <div class="chat-message bot">
                        <div class="message-content">
                            <div class="bot-avatar">🤖</div>
                            <div class="bubble">👋 Hi! I'm your AI Sales Assistant. Ask me about your leads or strategies!</div>
                        </div>
                    </div>
                    <!-- Suggestions Panel -->
                    <div class="chat-suggestions" id="chatSuggestions">
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🔍 Which leads to focus on?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">📊 Pipeline risks?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🚀 Campaign strategy?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">📈 Check sales velocity</div>
                    </div>
                </div>
                <div class="chat-footer">
                    <div class="input-wrapper">
                        <input type="text" id="chatInput" class="chat-input" placeholder="Ask anything..." onkeypress="handleChatEnter(event)">
                        <button class="chat-send-btn" onclick="sendChatMessage()">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', chatHTML);
}

function toggleChat() {
    const window = document.getElementById('chatWindow');
    const btn = document.querySelector('.chat-toggle-btn');
    window.classList.toggle('open');
    btn.classList.toggle('active');

    if (window.classList.contains('open')) {
        setTimeout(() => document.getElementById('chatInput').focus(), 300);
    }
}

function handleChatEnter(e) {
    if (e.key === 'Enter') sendChatMessage();
}

function sendSuggestion(el) {
    const text = el.innerText;
    // Don't auto-send, just fill input or send directly based on preference. 
    // User requested "Suggested Messages" feature usually implies checking content.
    // But for quick prompts, sending directly is often better UX. Let's send directly.
    addMessage(text, 'user');

    // Hide suggestions
    const suggestions = document.getElementById('chatSuggestions');
    if (suggestions) {
        suggestions.style.opacity = '0';
        setTimeout(() => suggestions.style.display = 'none', 300);
    }

    processBotResponse(text);
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    // Hide suggestions if present
    const suggestions = document.getElementById('chatSuggestions');
    if (suggestions && suggestions.style.display !== 'none') {
        suggestions.style.opacity = '0';
        setTimeout(() => suggestions.style.display = 'none', 300);
    }

    addMessage(msg, 'user');
    input.value = '';

    processBotResponse(msg);
}

async function processBotResponse(msg) {
    const typingId = showTyping();

    try {
        // Call Backend
        const res = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();

        removeTyping(typingId);
        addMessage(data.reply, 'bot');

    } catch (e) {
        console.error(e);
        removeTyping(typingId);
        addMessage("⚠️ Error: Could not connect to SalesSpark Brain.", 'bot');
    }
}

function addMessage(text, sender) {
    const body = document.getElementById('chatBody');
    const div = document.createElement('div');
    div.classList.add('chat-message', sender);

    if (sender === 'bot') {
        div.innerHTML = `
            <div class="message-content">
                <div class="bot-avatar">🤖</div>
                <div class="bubble">${text}</div>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="message-content">
                <div class="bubble">${text}</div>
            </div>
        `;
    }

    body.appendChild(div);

    // Smooth scroll to bottom
    body.scrollTo({
        top: body.scrollHeight,
        behavior: 'smooth'
    });
}

function showTyping() {
    const body = document.getElementById('chatBody');
    const id = 'typing-' + Date.now();
    const html = `
        <div class="chat-message bot typing" id="${id}">
            <div class="message-content">
                <div class="bot-avatar">🤖</div>
                <div class="bubble typing-bubble">
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
        </div>
    `;
    body.insertAdjacentHTML('beforeend', html);
    body.scrollTo({
        top: body.scrollHeight,
        behavior: 'smooth'
    });
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

