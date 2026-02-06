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
function initChatbot() {
    // 1. Inject HTML
    const chatHTML = `
        <div class="chatbot-widget">
            <button class="chat-toggle-btn" onclick="toggleChat()">💬</button>
            <div class="chat-window" id="chatWindow">
                <div class="chat-header">
                    <h3>🤖 SalesSpark Assistant</h3>
                    <button class="chat-close-btn" onclick="toggleChat()">×</button>
                </div>
                <div class="chat-body" id="chatBody">
                    <div class="chat-message bot">
                        👋 Hi! I'm your AI Sales Assistant. Ask me about your leads or strategies!
                    </div>
                    <!-- Suggestions Panel -->
                    <div class="chat-suggestions" id="chatSuggestions">
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🔍 Which leads should I focus on?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">📊 What risks are there in my pipeline?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🚀 Which campaign strategy should I use?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🧩 Explain what a warm lead means</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">📈 What does my sales momentum look like?</div>
                    </div>
                </div>
                <div class="chat-footer">
                    <input type="text" id="chatInput" class="chat-input" placeholder="Ask a question..." onkeypress="handleChatEnter(event)">
                    <button class="chat-send-btn" onclick="sendChatMessage()">➤</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', chatHTML);
}

function toggleChat() {
    const window = document.getElementById('chatWindow');
    window.classList.toggle('open');
    if (window.classList.contains('open')) {
        document.getElementById('chatInput').focus();
    }
}

function handleChatEnter(e) {
    if (e.key === 'Enter') sendChatMessage();
}

function sendSuggestion(el) {
    const text = el.innerText;
    document.getElementById('chatInput').value = text;
    sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    // Hide suggestions on first interaction
    const suggestions = document.getElementById('chatSuggestions');
    if (suggestions) suggestions.style.display = 'none';

    // Add User Message
    addMessage(msg, 'user');
    input.value = '';

    // Show Typing Indicator
    const typingId = showTyping();

    try {
        // Call Backend
        const res = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();

        // Remove Typing & Add Bot Response
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
    div.innerText = text;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
}

function showTyping() {
    const body = document.getElementById('chatBody');
    const id = 'typing-' + Date.now();
    const html = `
        <div class="typing-indicator" id="${id}">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    body.insertAdjacentHTML('beforeend', html);
    body.scrollTop = body.scrollHeight;
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
