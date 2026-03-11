/**
 * app.js — Global App Logic & SalesSparkAI Copilot Widget
 *
 * Features:
 *  - Sends `current_page` with every chat request for page-aware responses.
 *  - Sends last 3 conversation turns as `history` for context (token optimized).
 *  - Handles `action: "navigate"` responses by redirecting the browser.
 *  - Greeting shortcut: shows instant response without waiting for backend.
 *  - Maintains a lightweight in-memory chat history array.
 */

const STORAGE_KEY = 'salesSparkData_v2';

const defaultState = {
    campaigns: 0,
    leadsScored: 0,
    hotLeads: 0,
    totalScore: 0,
    history: []
};

let appState = { ...defaultState };

// ── Persistence ────────────────────────────────────────────────────────────────
function loadState() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        try { appState = JSON.parse(saved); }
        catch (e) { appState = { ...defaultState }; }
    }
}

function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
    window.dispatchEvent(new Event('stateUpdated'));
}

// ── Navigation highlight ───────────────────────────────────────────────────────
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav a').forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath.includes(href) || (currentPath.endsWith('/') && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// ── Page detection (sent to backend with every message) ────────────────────────
function getCurrentPage() {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('leads')) return 'leads';
    if (path.includes('market_intelligence')) return 'market';
    if (path.includes('sales_copilot')) return 'sales_copilot';
    if (path.includes('prediction')) return 'prediction';
    if (path.includes('tools')) return 'tools';
    return 'home';
}

// ── In-memory conversation history (last 6 turns max) ─────────────────────────
const chatHistory = [];   // [{role: "user"|"assistant", content: "..."}]

function addToHistory(role, content) {
    chatHistory.push({ role, content });
    // Keep only the last 6 entries (3 user + 3 assistant turns = token optimized)
    if (chatHistory.length > 6) chatHistory.splice(0, chatHistory.length - 6);
}

// ── Navigation action handler ──────────────────────────────────────────────────
const PAGE_URLS = {
    'sales_copilot': 'sales_copilot.html',
    'leads': 'leads.html',
    'tools': 'tools.html',
    'prediction': 'prediction.html',
    'market': 'market_intelligence.html',
};

// Page display names for a friendlier UX message
const PAGE_LABELS = {
    'sales_copilot': 'Sales Copilot',
    'leads': 'Leads',
    'tools': 'Tools',
    'prediction': 'Prediction',
    'market': 'Market Intelligence',
};

function handleNavigationAction(data) {
    const pageKey = data.page?.toLowerCase();
    const label = PAGE_LABELS[pageKey] || pageKey;
    // Use url from backend if provided, otherwise resolve from local map
    const url = data.url
        ? data.url.replace(/^\//, '')          // strip leading slash for relative path
        : PAGE_URLS[pageKey];

    if (url) {
        const navMsg = `
            <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:20px;">🔗</span>
                <div>
                    <div style="font-weight:600;">Opening <strong>${label}</strong>…</div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:3px;">Redirecting in a moment</div>
                </div>
            </div>`;
        addMessage(navMsg, 'bot');
        setTimeout(() => { window.location.href = url; }, 1400);
    } else {
        addMessage(data.response || "I couldn't identify that page.", 'bot');
    }
}

// ── Client-side greeting shortcut (instant, no API call) ──────────────────────
const GREETING_RE = /^\s*(hi|hello|hey|good\s*morning|good\s*afternoon|good\s*evening|howdy|sup|what'?s\s*up|yo)\s*[.!?]?\s*$/i;

function isGreeting(msg) { return GREETING_RE.test(msg.trim()); }

const INSTANT_GREETING =
    "👋 Hi there! I'm <strong>SalesSparkAI Copilot</strong> — your AI sales intelligence assistant.<br><br>" +
    "Here's what I can help with:<br>" +
    "• 🔥 <strong>Analyze leads</strong> — find your hottest prospects<br>" +
    "• 🚀 <strong>Launch campaigns</strong> — generate targeted strategies<br>" +
    "• 🗺️ <strong>Navigate the platform</strong> — just say \"Show my leads\"<br>" +
    "• 📊 <strong>Pipeline health</strong> — get a real-time overview<br><br>" +
    "<em>What would you like to explore today?</em>";

// ── Client-side product question shortcut (instant, no API call) ───────────────
const PRODUCT_Q_RE = /^\s*(what\s+(is|are|does)\s+(this|the|salessparkAI|sales\s*spark\s*ai)?\s*(website|platform|tool|app|product|system|software|it|salessparkAI|sales\s*spark\s*ai)[\s?]*)|(how\s+does\s+(this|the)?\s*(platform|tool|app|product|website|salessparkAI)?\s*works?[?]*)|(tell\s+me\s+about\s+(this|the)?\s*(platform|tool|salessparkAI|sales\s*spark\s*ai))|(what\s+can\s+(you|this\s+platform|salessparkAI)\s+do[?]*)|(what'?s?\s+(this|salessparkAI|sales\s*spark\s*ai)[?]*)/i;

function isProductQuestion(msg) { return PRODUCT_Q_RE.test(msg.trim()); }

const INSTANT_PRODUCT =
    "<strong>SalesSparkAI</strong> is an AI-powered sales enablement platform designed to help " +
    "sales teams analyze leads, generate outreach content, and optimize their sales strategy.<br><br>" +
    "🧰 <strong>Platform tools include:</strong><br>" +
    "• 🤖 <strong>AI Sales Copilot</strong> — pipeline insights &amp; next-best-action guidance<br>" +
    "• 🚀 <strong>Campaign Generator</strong> — multi-channel marketing strategies<br>" +
    "• 🎯 <strong>Sales Pitch Generator</strong> — persuasive outreach scripts<br>" +
    "• 📧 <strong>Email Outreach</strong> — personalized email drafts<br>" +
    "• ⚖️ <strong>Lead Scoring</strong> — scores leads 0-100 (Hot / Warm / Cold)<br>" +
    "• 📱 <strong>Social Media Generator</strong> — posts and hashtags<br>" +
    "• 📊 <strong>Market Intelligence</strong> — demand, competition &amp; opportunity analysis<br>" +
    "• 🔒 <strong>Deal Tools</strong> — closure strategies and follow-up plans<br><br>" +
    "<em>Want me to open a specific tool or analyze your pipeline?</em>";

// ── Client-side navigation intent detection (instant, no API call) ────────────
// Maps each page key to a regex that matches common navigation phrasings.
const NAVIGATION_INTENTS = {
    'sales_copilot': /\b(open|show|go\s*to|take\s*me\s*to)\s*(sales\s*)?copilot\b/i,
    'leads': /\b(open|show|go\s*to|take\s*me\s*to|view|see)\s*(my\s*)?leads?\b/i,
    'tools': /\b(open|show|go\s*to|take\s*me\s*to)\s*(tools?|campaign\s*generator)\b/i,
    'prediction': /\b(open|show|go\s*to|take\s*me\s*to)\s*(prediction|prediction\s*page|campaign\s*prediction)\b/i,
    'market': /\b(open|show|go\s*to|take\s*me\s*to)\s*(market|market\s*insights?|market\s*intelligence)\b/i,
};

function detectNavigationIntent(msg) {
    const text = msg.trim();
    for (const [pageKey, pattern] of Object.entries(NAVIGATION_INTENTS)) {
        if (pattern.test(text)) {
            const label = PAGE_LABELS[pageKey] || pageKey;
            const url   = PAGE_URLS[pageKey];
            return { page: pageKey, label, url };
        }
    }
    return null;
}

// ── Client-side feature guidance (instant, page-aware, no API call) ───────────
// Returns an HTML guidance string when the user asks how to use a feature,
// keyed by the current page. Returns null when no match found.
const FEATURE_GUIDANCE_RE = /\b(how\s+(do\s+i|can\s+i|to)|how\s+does?|guide\s+me|help\s+me\s+(use|with)|what\s+can\s+i\s+do|explain)\b/i;

const FEATURE_GUIDANCE = {
    tools: (
        "📋 <strong>Campaign Generator — How to use:</strong><br>" +
        "1. Go to the <strong>Tools</strong> page.<br>" +
        "2. Select your target industry and audience in the Campaign Generator card.<br>" +
        "3. Click <em>Generate Campaign</em> — the AI builds a multi-channel strategy instantly.<br>" +
        "4. Copy or download the output for LinkedIn, Email, and Social channels.<br><br>" +
        "<em>Need a pitch or email instead? Try the Pitch Generator or Email Outreach on the same page.</em>"
    ),
    leads: (
        "🎯 <strong>Lead Scores — How to read them:</strong><br>" +
        "• 🔥 <strong>Hot</strong> (≥ 80) — High priority. Schedule a call within 48 hours.<br>" +
        "• 🌡️ <strong>Warm</strong> (55–79) — Nurture with personalised outreach.<br>" +
        "• ❄️ <strong>Cold</strong> (< 55) — Re-engage with a campaign or discount offer.<br><br>" +
        "Scroll down to <strong>Deal Tools</strong> on this page to get AI-powered closing strategies for any lead."
    ),
    sales_copilot: (
        "🤖 <strong>Sales Copilot — How to use:</strong><br>" +
        "• The KPI cards at the top show your live pipeline (total, hot, warm, cold leads).<br>" +
        "• The <em>AI Insights</em> panel gives you data-driven recommendations updated in real time.<br>" +
        "• <em>Next Best Actions</em> lists your top-priority leads to contact today.<br>" +
        "• Use the <em>Refresh</em> button to pull the latest data from the backend.<br><br>" +
        "<em>Ask me 'how many hot leads do I have?' for a live pipeline summary.</em>"
    ),
    market: (
        "📊 <strong>Market Intelligence — How to use:</strong><br>" +
        "1. Enter the industry, region, or product segment you want to analyse.<br>" +
        "2. Click <em>Analyse Market</em> — the AI returns demand signals, competition, and opportunities.<br>" +
        "3. Use the insights to target the right leads and position your campaigns.<br><br>" +
        "<em>Combine Market Intelligence with the Campaign Generator for best results.</em>"
    ),
    prediction: (
        "🔮 <strong>Campaign Prediction — How to use:</strong><br>" +
        "1. Describe your campaign (channel, audience, offer).<br>" +
        "2. Click <em>Predict</em> — the AI estimates engagement and conversion rates.<br>" +
        "3. Adjust your strategy based on the predicted outcome before launching.<br><br>" +
        "<em>Run predictions before any major campaign to optimise your spend.</em>"
    ),
};

function detectFeatureGuidance(msg, page) {
    // Only trigger on messages that contain a 'how to' / guidance pattern
    if (!FEATURE_GUIDANCE_RE.test(msg)) return null;
    // Return page-specific guidance if available
    return FEATURE_GUIDANCE[page] || null;
}

// ── Initialization ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadState();
    highlightActiveNav();
    initChatbot();
});

// ── Chatbot Widget ─────────────────────────────────────────────────────────────
function generateSessionId() {
    return 'sess_' + Math.random().toString(36).substr(2, 9);
}
const CHAT_SESSION_ID = generateSessionId();

function initChatbot() {
    const chatHTML = `
        <div class="chatbot-widget">
            <button class="chat-toggle-btn" onclick="toggleChat()" title="SalesSparkAI Copilot">
                <span class="chat-icon">🤖</span>
                <span class="chat-pulse"></span>
            </button>
            <div class="chat-window" id="chatWindow">
                <div class="chat-header">
                    <div class="header-info">
                        <h3>SalesSpark AI</h3>
                        <span class="header-subtitle">Your sales intelligence copilot</span>
                    </div>
                    <button class="chat-close-btn" onclick="toggleChat()" title="Close">
                         <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="chat-divider"></div>
                <div class="chat-body" id="chatBody">
                    <div class="chat-message bot">
                        <div class="message-content">
                            <div class="bot-avatar">🤖</div>
                            <div class="bubble">
                                👋 Hi! I'm <strong>SalesSparkAI Copilot</strong>.<br>
                                I can help you analyze leads, navigate the platform, and generate campaigns.<br><br>
                                <em>Try one of the suggestions below ↓</em>
                            </div>
                        </div>
                    </div>
                    <div class="chat-suggestions" id="chatSuggestions">
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🔍 Which leads are hot?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">📊 How is my pipeline?</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">🚀 Show my leads</div>
                        <div class="suggestion-chip" onclick="sendSuggestion(this)">💡 What features are available?</div>
                    </div>
                </div>
                <div class="chat-footer">
                    <div class="input-wrapper">
                        <input type="text" id="chatInput" class="chat-input"
                            placeholder="Ask anything or say 'Show leads'..."
                            onkeypress="handleChatEnter(event)">
                        <button class="chat-send-btn" onclick="sendChatMessage()" title="Send">
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
    const win = document.getElementById('chatWindow');
    const btn = document.querySelector('.chat-toggle-btn');
    win.classList.toggle('open');
    btn.classList.toggle('active');
    if (win.classList.contains('open')) {
        setTimeout(() => document.getElementById('chatInput').focus(), 300);
    }
}

function handleChatEnter(e) {
    if (e.key === 'Enter') sendChatMessage();
}

function sendSuggestion(el) {
    // Strip leading emoji + whitespace from chip text
    const text = el.innerText.replace(/^[\u{1F000}-\u{1FFFF}\u{2600}-\u{27FF}\uD83C-\uDBFF\uDC00-\uDFFF]\s*/u, '').trim();
    addMessage(el.innerText, 'user');  // Show the original chip text with emoji to user
    hideSuggestions();
    processBotResponse(text);
}

function hideSuggestions() {
    const suggestions = document.getElementById('chatSuggestions');
    if (suggestions && suggestions.style.display !== 'none') {
        suggestions.style.opacity = '0';
        setTimeout(() => suggestions.style.display = 'none', 300);
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    hideSuggestions();
    addMessage(msg, 'user');
    input.value = '';
    processBotResponse(msg);
}

async function processBotResponse(msg) {
    if (isGreeting(msg)) {
        addToHistory('user', msg);
        addToHistory('assistant', INSTANT_GREETING);
        addMessage(INSTANT_GREETING, 'bot');
        return;
    }

    if (isProductQuestion(msg)) {
        addToHistory('user', msg);
        addToHistory('assistant', INSTANT_PRODUCT);
        addMessage(INSTANT_PRODUCT, 'bot');
        return;
    }

    const navIntent = detectNavigationIntent(msg);
    if (navIntent) {
        addToHistory('user', msg);
        const navReply = `Opening <strong>${navIntent.label}</strong>...`;
        addToHistory('assistant', navReply);
        handleNavigationAction({ page: navIntent.page, url: navIntent.url, response: navReply });
        return;
    }

    const page = getCurrentPage();
    const guidance = detectFeatureGuidance(msg, page);
    if (guidance) {
        addToHistory('user', msg);
        addToHistory('assistant', guidance);
        addMessage(guidance, 'bot');
        return;
    }

    const typingId = showTyping();

    try {
        const res = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg,
                session_id: CHAT_SESSION_ID,
                current_page: getCurrentPage(),
                history: chatHistory.slice(-6),
            })
        });

        const data = await res.json();
        removeTyping(typingId);

        if (data.error) {
            addMessage(`Error: ${data.error}`, 'bot');
            return;
        }

        if (data.action === 'navigate') {
            addToHistory('user', msg);
            addToHistory('assistant', data.response || '');
            handleNavigationAction(data);
            if (Array.isArray(data.suggestions) && data.suggestions.length) {
                updateSuggestions(data.suggestions);
            }
            return;
        }

        if (data.action === 'tool_result' || data.action === 'multi_step') {
            const reply = formatToolResult(data);
            addMessage(reply, 'bot');
            addToHistory('user', msg);
            addToHistory('assistant', data.response || reply);
            if (Array.isArray(data.suggestions) && data.suggestions.length) {
                updateSuggestions(data.suggestions);
            }
            return;
        }

        const reply = data.response || 'No response received.';
        addMessage(reply, 'bot');
        addToHistory('user', msg);
        addToHistory('assistant', reply);

        if (Array.isArray(data.suggestions) && data.suggestions.length) {
            updateSuggestions(data.suggestions);
        }

    } catch (e) {
        console.error('[Chat] Network error:', e);
        removeTyping(typingId);
        addMessage('Could not connect to SalesSpark Brain. Is the server running?', 'bot');
    }
}

function formatToolResult(data) {
    if (data.action === 'multi_step' && Array.isArray(data.steps)) {
        return `<strong>${data.response || 'Workflow generated.'}</strong><br><br>${data.steps.join('<br>')}`;
    }

    const result = data.result || {};
    if (data.tool === 'generate_campaign') {
        return `<strong>${data.response}</strong><br><br><b>Theme:</b> ${result.theme || ''}<br><b>Strategy:</b> ${result.marketing_strategy || ''}<br><b>CTA:</b> ${result.cta || ''}`;
    }
    if (data.tool === 'generate_email') {
        return `<strong>${data.response}</strong><br><br><b>Subject:</b> ${result.subject || ''}<br><pre>${result.body || ''}</pre>`;
    }
    if (data.tool === 'generate_pitch') {
        return `<strong>${data.response}</strong><br><br><b>Opening:</b> ${result.opening_hook || ''}<br><b>Positioning:</b> ${result.product_positioning || ''}<br><b>Closing:</b> ${result.closing_statement || ''}`;
    }
    if (data.tool === 'analyze_leads') {
        return `<strong>${data.response}</strong>`;
    }
    return data.response || 'Done.';
}
// ── UI helpers ─────────────────────────────────────────────────────────────────
function updateSuggestions(items) {
    const container = document.getElementById('chatSuggestions');
    if (!container) return;
    const emojis = ['🔍', '📊', '🚀', '💡', '🧠'];
    container.innerHTML = items.map((item, i) =>
        `<div class="suggestion-chip" onclick="sendSuggestion(this)">${emojis[i % emojis.length]} ${item}</div>`
    ).join('');
    container.style.display = 'flex';
    setTimeout(() => container.style.opacity = '1', 100);
}

function addMessage(text, sender) {
    const body = document.getElementById('chatBody');
    const div = document.createElement('div');
    div.classList.add('chat-message', sender);
    div.innerHTML = sender === 'bot'
        ? `<div class="message-content"><div class="bot-avatar">🤖</div><div class="bubble">${text}</div></div>`
        : `<div class="message-content"><div class="bubble">${text}</div></div>`;
    body.appendChild(div);
    body.scrollTo({ top: body.scrollHeight, behavior: 'smooth' });
}

function showTyping() {
    const body = document.getElementById('chatBody');
    const id = 'typing-' + Date.now();
    body.insertAdjacentHTML('beforeend', `
        <div class="chat-message bot typing" id="${id}">
            <div class="message-content">
                <div class="bot-avatar">🤖</div>
                <div class="bubble typing-bubble">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
            </div>
        </div>`);
    body.scrollTo({ top: body.scrollHeight, behavior: 'smooth' });
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}








