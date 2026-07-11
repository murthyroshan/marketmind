/**
 * app.js — Global app logic & SalesSparkAI Copilot widget.
 *
 * The copilot is a streaming, tool-calling AI agent:
 *  - Streams tokens live from POST /chat/stream (Server-Sent Events), with an
 *    automatic fallback to POST /chat if streaming is unavailable.
 *  - Persists the conversation, session id, and open/closed state in
 *    localStorage so it survives page navigation (the agent can navigate you
 *    between pages without losing context).
 *  - Renders rich cards for tool results (campaigns, emails, pitches, actions).
 *  - Zero-latency client shortcuts for greetings, product questions, page
 *    navigation, and page guidance (no round-trip to the server).
 *  - Polish: copy, regenerate, stop-generating, timestamps, clear, voice input.
 */

const API_BASE = 'http://127.0.0.1:8000';

// ── Shared HTML escaping (XSS-safe) ─────────────────────────────────────────────
function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function stripHtml(html) {
    const d = document.createElement('div');
    d.innerHTML = html;
    return (d.textContent || '').trim();
}

// ── Navigation highlight ────────────────────────────────────────────────────────
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('nav a').forEach(link => {
        const href = link.getAttribute('href') || '';
        if ((href && currentPath.includes(href)) || (currentPath.endsWith('/') && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// ── Page detection (sent to backend with every message) ─────────────────────────
function getCurrentPage() {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('leads')) return 'leads';
    if (path.includes('market_intelligence')) return 'market';
    if (path.includes('sales_copilot')) return 'sales_copilot';
    if (path.includes('prediction')) return 'prediction';
    if (path.includes('tools')) return 'tools';
    return 'home';
}

const PAGE_URLS = {
    'home': 'index.html', 'sales_copilot': 'sales_copilot.html', 'leads': 'leads.html',
    'tools': 'tools.html', 'prediction': 'prediction.html', 'market': 'market_intelligence.html',
};
const PAGE_LABELS = {
    'home': 'Home', 'sales_copilot': 'Sales Copilot', 'leads': 'Leads',
    'tools': 'Tools', 'prediction': 'Prediction', 'market': 'Market Intelligence',
};

// ── Persistent chat memory (survives navigation) ────────────────────────────────
const CHAT_KEYS = {
    session: 'salesspark_chat_session',
    transcript: 'salesspark_chat_transcript',
    history: 'salesspark_chat_history',
    open: 'salesspark_chat_open',
    briefing: 'salesspark_chat_briefing',
};

function getSessionId() {
    let id = localStorage.getItem(CHAT_KEYS.session);
    if (!id) {
        id = 'sess_' + Math.random().toString(36).slice(2, 11);
        localStorage.setItem(CHAT_KEYS.session, id);
    }
    return id;
}
const CHAT_SESSION_ID = getSessionId();

// chatHistory = raw text turns sent to the AI. transcript = rendered UI messages.
let chatHistory = loadJSON(CHAT_KEYS.history, []);
let transcript = loadJSON(CHAT_KEYS.transcript, []);
let isStreaming = false;
let streamController = null;

function loadJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; }
    catch (e) { return fallback; }
}
function saveHistory() {
    chatHistory = chatHistory.slice(-12);
    localStorage.setItem(CHAT_KEYS.history, JSON.stringify(chatHistory));
}
function addToHistory(role, content) {
    chatHistory.push({ role, content });
    saveHistory();
}
// The turn being sent is already in chatHistory (addUserMessage runs first) and the
// backend appends it again as the final user message, so send only what came before
// it — otherwise the model sees the same question twice.
function priorHistory() {
    const prior = chatHistory[chatHistory.length - 1]?.role === 'user'
        ? chatHistory.slice(0, -1)
        : chatHistory;
    return prior.slice(-8);
}
function saveTranscript() {
    transcript = transcript.slice(-60);
    localStorage.setItem(CHAT_KEYS.transcript, JSON.stringify(transcript));
}

// ── Client-side greeting shortcut (instant, no API call) ────────────────────────
const GREETING_RE = /^\s*(hi|hello|hey|good\s*morning|good\s*afternoon|good\s*evening|howdy|sup|what'?s\s*up|yo)\s*[.!?]?\s*$/i;
function isGreeting(msg) { return GREETING_RE.test(msg.trim()); }

const INSTANT_GREETING =
    "Ready. I can score leads, plan deals, draft outreach, or take you to any page.<br><br>" +
    "<em>What are we working on?</em>";

// ── Client-side product question shortcut (instant, no API call) ────────────────
const PRODUCT_Q_RE = /^\s*(what\s+(is|are|does)\s+(this|the|salessparkAI|sales\s*spark\s*ai)?\s*(website|platform|tool|app|product|system|software|it|salessparkAI|sales\s*spark\s*ai)[\s?]*)|(how\s+does\s+(this|the)?\s*(platform|tool|app|product|website|salessparkAI)?\s*works?[?]*)|(tell\s+me\s+about\s+(this|the)?\s*(platform|tool|salessparkAI|sales\s*spark\s*ai))|(what\s+can\s+(you|this\s+platform|salessparkAI)\s+do[?]*)|(what'?s?\s+(this|salessparkAI|sales\s*spark\s*ai)[?]*)/i;
function isProductQuestion(msg) { return PRODUCT_Q_RE.test(msg.trim()); }

const INSTANT_PRODUCT =
    "<strong>SalesSparkAI</strong> is an AI sales platform — it scores your leads, " +
    "generates campaigns, emails and pitches, and reads the market for you.<br><br>" +
    "<em>Want a pipeline check, or should I open a tool?</em>";

// ── Client-side navigation intent detection (instant, no API call) ──────────────
const NAVIGATION_INTENTS = {
    'home': /\b(open|show|go\s*to|take\s*me\s*to|back\s*to)\s*(home|landing|landing\s*page|index)\b/i,
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
            return { page: pageKey, label: PAGE_LABELS[pageKey] || pageKey, url: PAGE_URLS[pageKey] };
        }
    }
    return null;
}

// ── Client-side page-aware feature guidance (instant, no API call) ──────────────
// This only answers "how does this page work" questions. It must NOT swallow real
// work — "How do I close Acme?" and "How can I improve campaign performance?" are
// questions for the agent, so the pattern requires an explicit reference to the
// page/tool itself rather than matching any "how do I" phrasing.
const FEATURE_GUIDANCE_RE =
    /\b(how\s+do(es)?\s+(this|it)\s+(page\s+|tool\s+|thing\s+)?work|how\s+do\s+i\s+use\s+(this|it)|help\s+me\s+use\s+(this|it)|guide\s+me\s+(through|around)|what\s+(can\s+i\s+do|is\s+there\s+to\s+do)\s+(here|on\s+this\s+page)|what\s+is\s+this\s+page\s+for)\b/i;
const FEATURE_GUIDANCE = {
    tools: (
        "<strong>Campaign Generator:</strong> pick an industry + audience, hit " +
        "<em>Generate Campaign</em>, and you get a multi-channel strategy.<br><br>" +
        "<em>Pitch and Email generators are on the same page.</em>"
    ),
    leads: (
        "<strong>Lead scores:</strong> Hot (80+) — call within 48h · " +
        "Warm (55–79) — nurture · Cold (&lt;55) — re-engage.<br><br>" +
        "<em>Deal Tools below gives closing strategies for any lead.</em>"
    ),
    sales_copilot: (
        "<strong>Sales Copilot:</strong> KPI cards show your live pipeline, and " +
        "<em>Next Best Actions</em> lists who to contact today.<br><br>" +
        "<em>Ask \"how many hot leads do I have?\" for a live count.</em>"
    ),
    market: (
        "<strong>Market Intelligence:</strong> enter an industry or segment and hit " +
        "<em>Analyse Market</em> — you get demand, competition, and opportunities.<br><br>" +
        "<em>Pair it with the Campaign Generator.</em>"
    ),
    prediction: (
        "<strong>Campaign Prediction:</strong> choose a channel + goal and hit " +
        "<em>Predict</em> — the AI estimates engagement and conversion before you launch."
    ),
};
function detectFeatureGuidance(msg, page) {
    if (!FEATURE_GUIDANCE_RE.test(msg)) return null;
    return FEATURE_GUIDANCE[page] || null;
}

// ── Lightweight, XSS-safe markdown rendering ────────────────────────────────────
function renderRichText(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // "- " / "• " bullet lines. This has to run against the newlines, before they
    // become <br> — matching on "<br>" here would only ever catch the first line.
    html = html.replace(/(^|\n)\s*[-•]\s+/g, '$1&nbsp;&nbsp;• ');
    html = html.replace(/\n/g, '<br>');
    return html;
}

// ── Rich tool-result cards ──────────────────────────────────────────────────────
function renderToolCard(ev) {
    const r = ev.result || {};
    // Every card carries copy + download buttons; both read the card's own text.
    const wrap = (title, inner, filename) =>
        `<div class="tool-card" data-filename="${escapeHtml(filename || 'salesspark-asset')}">
            <div class="tool-card-head">
                <div class="tool-card-title">${escapeHtml(title)}</div>
                <div class="tool-card-actions">
                    <button class="tool-card-btn" onclick="copyCard(this)" title="Copy" aria-label="Copy">⧉</button>
                    <button class="tool-card-btn" onclick="downloadCard(this)" title="Download as .txt" aria-label="Download">⭳</button>
                </div>
            </div>
            <div class="tool-card-body">${inner}</div>
        </div>`;
    const row = (label, val) =>
        val ? `<div class="tool-row"><span class="tool-label">${escapeHtml(label)}</span> ${escapeHtml(val)}</div>` : '';
    const pct = (v) => (v || v === 0) ? `${v}%` : '';

    switch (ev.tool) {
        case 'generate_campaign':
            return wrap('CAMPAIGN', row('Theme', r.theme) + row('Strategy', r.marketing_strategy) +
                row('Messaging', r.messaging_approach) + row('CTA', r.cta) +
                row('Expected', r.outcome || r.expected_outcome), 'campaign');
        case 'generate_email':
            return wrap('OUTREACH EMAIL',
                row('Subject', r.subject) +
                `<pre class="tool-pre">${escapeHtml(r.body || '')}</pre>` +
                row('Follow-up', r.follow_up_suggestion || r.follow_up_tip), 'outreach-email');
        case 'generate_pitch':
            return wrap('SALES PITCH', row('Hook', r.opening_hook) + row('Problem', r.problem_framing) +
                row('Positioning', r.product_positioning) + row('Objection', r.objection_handling) +
                row('Close', r.closing_statement), 'sales-pitch');
        case 'generate_social':
            return wrap('SOCIAL POST',
                `<pre class="tool-pre">${escapeHtml(r.caption || '')}</pre>` +
                row('Hashtags', r.hashtags) + row('Tone', r.tone), 'social-post');
        case 'analyze_market':
            return wrap('MARKET INTELLIGENCE', row('Trend', r.market_trend_summary) + row('Demand', r.demand_level) +
                row('Competition', r.competition_overview) + row('Opportunity', r.opportunity_insights), 'market-analysis');
        case 'next_actions': {
            const items = (r.actions || []).slice(0, 5).map(a =>
                `<div class="tool-row"><span class="tool-label">${escapeHtml(a.company || 'Lead')}</span> ${escapeHtml(a.action || '')}</div>`).join('');
            return wrap('NEXT BEST ACTIONS', items || '<div class="tool-row">No actions yet.</div>', 'next-actions');
        }
        case 'list_leads': {
            const items = (r.leads || []).map(l =>
                `<div class="tool-row"><span class="tool-label">${escapeHtml(l.company || 'Lead')}</span> ` +
                `${escapeHtml(l.score)}/100 · ${escapeHtml(l.category)} · ${escapeHtml(l.deal_stage || 'Prospecting')}</div>`).join('');
            return wrap('LEADS', items || '<div class="tool-row">No leads found.</div>', 'leads');
        }
        case 'score_lead':
            return wrap('LEAD SCORE', row('Company', r.company) +
                row('Score', `${r.score}/100 (${r.category})`) +
                row('Recommendation', r.recommendation) + row('Why', r.explanation), 'lead-score');
        case 'deal_strategy':
            return wrap(`CLOSING PLAN${r.company ? ' — ' + r.company : ''}`,
                row('Urgency', r.urgency_level) + row('Strategy', r.closing_strategy) +
                row('Discount', r.discount_range) + row('Objections', r.objection_focus) +
                row('Next step', r.recommended_next_step), 'closing-plan');
        case 'followup_plan': {
            const plan = r.plan || {};
            const steps = Object.keys(plan).map(k => row(k.toUpperCase(), plan[k])).join('');
            return wrap(`FOLLOW-UP PLAN${r.company ? ' — ' + r.company : ''}`,
                steps + row('Note', r.note), 'followup-plan');
        }
        case 'predict_campaign':
            return wrap('CAMPAIGN PREDICTION',
                row('Engagement', pct(r.engagement_prob)) + row('Conversion', pct(r.conversion_prob)) +
                row('Risk', r.risk_level) + row('Reasoning', r.reasoning) +
                row('Suggestions', Array.isArray(r.suggestions) ? r.suggestions.join(' · ') : r.suggestions),
                'campaign-prediction');
        default:
            return '';
    }
}

// ── Export: copy / download a generated asset ───────────────────────────────────
function cardText(btn) {
    const card = btn.closest('.tool-card');
    if (!card) return { text: '', name: 'asset' };
    const title = card.querySelector('.tool-card-title');
    const body = card.querySelector('.tool-card-body');
    const text = `${title ? title.innerText.trim() : ''}\n\n${body ? body.innerText.trim() : ''}`;
    return { text: text.trim(), name: card.dataset.filename || 'asset' };
}

function copyCard(btn) {
    const { text } = cardText(btn);
    navigator.clipboard.writeText(text).then(() => {
        const old = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = old; }, 1200);
    }).catch(() => {});
}

function downloadCard(btn) {
    const { text, name } = cardText(btn);
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ── Live status strip ───────────────────────────────────────────────────────────
// The ticker across the top of every page. Numbers count up rather than snapping,
// so the terminal reads as live instrumentation instead of static text.
function countUp(el, target, suffix = '') {
    if (!el) return;
    const value = Number(target);
    if (!isFinite(value)) { el.textContent = String(target); return; }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        el.textContent = value + suffix;
        return;
    }
    const duration = 650;
    const start = performance.now();
    const step = (now) => {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        const current = value % 1 ? (value * eased).toFixed(1) : Math.round(value * eased);
        el.textContent = current + suffix;
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

async function loadStatusStrip() {
    const strip = document.getElementById('statusStrip');
    if (!strip) return;
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        if (!res.ok) throw new Error('offline');
        const m = (await res.json()).metrics || {};
        countUp(document.getElementById('st-total'), m.total_leads);
        countUp(document.getElementById('st-hot'), m.hot_leads);
        countUp(document.getElementById('st-warm'), m.warm_leads);
        countUp(document.getElementById('st-avg'), m.avg_lead_score);
        const health = document.getElementById('st-health');
        if (health) health.textContent = (m.lead_quality_trend || '—').toUpperCase();
    } catch (e) {
        strip.querySelectorAll('b').forEach(b => { b.textContent = '—'; });
        const live = strip.querySelector('.status-live');
        if (live) live.style.background = 'var(--hot)';
        const first = strip.querySelector('.status-item');
        if (first) first.lastChild.textContent = ' OFFLINE';
    }
}

// ── Live board (home page) ──────────────────────────────────────────────────────
async function loadBoard() {
    const board = document.getElementById('dist');
    const canvas = document.getElementById('heroCanvas');
    if (!board && !canvas) return;
    try {
        const [dashRes, leadsRes] = await Promise.all([
            fetch(`${API_BASE}/dashboard`),
            fetch(`${API_BASE}/leads`),
        ]);
        const m = (await dashRes.json()).metrics || {};
        const leads = (await leadsRes.json()).leads || [];

        drawHeroChart(leads);
        buildTicker(leads);

        // Pipeline value = the money actually sitting in the book.
        const value = leads.reduce((sum, l) => sum + (Number(l.budget) || 0), 0);
        const valueEl = document.getElementById('pv-value');
        if (valueEl) {
            const fmt = (n) => '$' + Math.round(n).toLocaleString();
            animate(0, value, 900, (v) => { valueEl.textContent = fmt(v); });
        }
        setText('pv-sub', `${m.total_leads || 0} leads · avg ${m.avg_lead_score || 0}/100 · ${m.total_campaigns || 0} campaigns`);

        const delta = document.getElementById('pv-delta');
        if (delta) {
            const trend = m.lead_quality_trend || 'Stable';
            delta.textContent = trend === 'Improving' ? '▲ IMPROVING'
                : trend === 'Needs Attention' ? '▼ NEEDS ATTENTION' : '■ STABLE';
            delta.className = 'board-delta ' + (trend === 'Improving' ? 'up' : trend === 'Needs Attention' ? 'down' : '');
        }

        const total = Math.max(1, m.total_leads || 0);
        [['hot', m.hot_leads], ['warm', m.warm_leads], ['cold', m.cold_leads]].forEach(([k, n]) => {
            const count = n || 0;
            const pct = Math.round((count / total) * 100);
            countUp(document.getElementById('d-' + k), count);
            setText('p-' + k, pct + '%');
            const bar = document.getElementById('b-' + k);
            if (bar) requestAnimationFrame(() => { bar.style.width = pct + '%'; });
        });

        const top = document.getElementById('top-leads');
        if (top) {
            const best = leads.slice(0, 5);
            top.innerHTML = best.length ? best.map(l => {
                const cat = (l.category || 'Cold').toLowerCase();
                return `<a class="top-lead" href="leads.html">
                    <span>
                        <span class="top-lead-co">${escapeHtml(l.company || '—')}</span>
                        <span class="top-lead-meta">${escapeHtml(l.deal_stage || 'Prospecting')} · ${escapeHtml(l.category)}</span>
                    </span>
                    <span class="top-lead-score" style="color:var(--${cat})">${escapeHtml(l.score)}</span>
                </a>`;
            }).join('') : '<div class="panel-empty">No leads yet</div>';
        }
    } catch (e) {
        setText('pv-value', '—');
        setText('pv-sub', 'Backend offline');
        const top = document.getElementById('top-leads');
        if (top) top.innerHTML = '<div class="panel-empty">Backend offline</div>';
    }
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function animate(from, to, duration, onFrame) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return onFrame(to);
    const start = performance.now();
    const step = (now) => {
        const p = Math.min(1, (now - start) / duration);
        onFrame(from + (to - from) * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// ── Atmosphere layers ───────────────────────────────────────────────────────────
// Behind the content: a drifting ghost market (canvas), a spotlight that tracks
// the cursor, HUD chrome at the viewport corners, grain, and a vignette.
function initAtmosphere() {
    ['bgfx', 'spotlight', 'hud', 'grain', 'vignette'].forEach(cls => {
        if (document.querySelector('.' + cls)) return;
        const el = document.createElement(cls === 'bgfx' ? 'canvas' : 'div');
        el.className = cls;
        if (cls === 'hud') {
            el.innerHTML = '<i class="hud-tl"></i><i class="hud-tr"></i><i class="hud-bl"></i><i class="hud-br"></i>';
        }
        document.body.appendChild(el);
    });
    initSpotlight();
    initGhostMarket();
}

function initSpotlight() {
    const el = document.querySelector('.spotlight');
    if (!el || window.matchMedia('(pointer: coarse)').matches) return;
    let raf = null, x = 0, y = 0;
    window.addEventListener('mousemove', (e) => {
        x = e.clientX; y = e.clientY;
        if (raf) return;
        raf = requestAnimationFrame(() => {
            el.style.setProperty('--mx', x + 'px');
            el.style.setProperty('--my', y + 'px');
            el.style.opacity = '1';
            raf = null;
        });
    });
}

// A slow, layered market drifting behind the page. Deterministic pseudo-noise,
// no library, ~60fps, pauses when the tab is hidden.
function initGhostMarket() {
    const canvas = document.querySelector('.bgfx');
    if (!canvas) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const ctx = canvas.getContext('2d');

    let W = 0, H = 0, dpr = Math.min(2, window.devicePixelRatio || 1);
    function size() {
        W = canvas.clientWidth;
        H = canvas.clientHeight;
        canvas.width = Math.floor(W * dpr);
        canvas.height = Math.floor(H * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    size();
    window.addEventListener('resize', size);

    // Smooth value noise — a cheap 1D perlin stand-in.
    const wave = (x, seed) =>
        Math.sin(x * 0.0021 + seed) * 0.55 +
        Math.sin(x * 0.0057 + seed * 2.3) * 0.28 +
        Math.sin(x * 0.0134 + seed * 4.7) * 0.17;

    // depth = how far each layer parallaxes against the scroll (0 = pinned, 1 = tracks)
    const LAYERS = [
        { seed: 1.7, amp: 0.11, y: 0.28, speed: 0.016, depth: 0.06, glow: 5,
          color: 'rgba(255,176,32,0.24)', fill: 'rgba(255,176,32,0.028)', w: 1.1 },
        { seed: 4.2, amp: 0.09, y: 0.50, speed: 0.024, depth: 0.10, glow: 4,
          color: 'rgba(109,127,138,0.22)', fill: 'rgba(109,127,138,0.026)', w: 1 },
        { seed: 9.1, amp: 0.07, y: 0.70, speed: 0.010, depth: 0.14, glow: 0,
          color: 'rgba(255,92,77,0.14)', fill: 'rgba(255,92,77,0.018)', w: 1 },
    ];

    let t = 0;
    let running = true;
    let scrollY = 0;
    window.addEventListener('scroll', () => {
        scrollY = window.scrollY;
        // the CSS grid parallaxes too (see --gy in style.css)
        document.documentElement.style.setProperty('--gy', scrollY + 'px');
    }, { passive: true });

    document.addEventListener('visibilitychange', () => {
        running = !document.hidden;
        if (running) requestAnimationFrame(frame);
    });

    function frame() {
        if (!running) return;
        t += 1;
        ctx.clearRect(0, 0, W, H);

        LAYERS.forEach((L) => {
            // Parallax: each layer lags the scroll by its own depth, so the
            // background has volume instead of being a flat sticker.
            const base = H * L.y - scrollY * L.depth;
            const amp = H * L.amp;
            const off = t * L.speed * 14;

            const path = (moveFirst) => {
                for (let x = 0; x <= W; x += 6) {
                    const y = base + wave(x + off, L.seed) * amp;
                    (x === 0 && moveFirst) ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
                }
            };

            ctx.beginPath();
            ctx.moveTo(0, H);
            path(false);
            ctx.lineTo(W, H);
            ctx.closePath();
            ctx.fillStyle = L.fill;
            ctx.fill();

            ctx.save();
            ctx.shadowColor = L.color;
            ctx.shadowBlur = L.glow;
            ctx.beginPath();
            path(true);
            ctx.strokeStyle = L.color;
            ctx.lineWidth = L.w;
            ctx.stroke();
            ctx.restore();
        });

        requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
}

// ── Hero chart ──────────────────────────────────────────────────────────────────
// Every lead is a bar, ordered by score, coloured by category — the score book
// drawn as a market depth chart. Bars grow in on load; the top lead pulses.
function drawHeroChart(leads) {
    const canvas = document.getElementById('heroCanvas');
    if (!canvas || !leads.length) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const PAD = { t: 10, r: 8, b: 8, l: 8 };
    const data = [...leads].sort((a, b) => (b.score || 0) - (a.score || 0));
    const COLOR = { hot: '#ff5c4d', warm: '#ffb020', cold: '#6d7f8a' };

    const hi = document.getElementById('chartHi');
    if (hi) hi.textContent = `HIGH ${data[0].score} · LOW ${data[data.length - 1].score}`;

    const axis = document.getElementById('chartAxis');
    if (axis) {
        axis.innerHTML = `<span>${escapeHtml(data[0].company || '')}</span>` +
            `<span>${data.length} POSITIONS</span>` +
            `<span>${escapeHtml(data[data.length - 1].company || '')}</span>`;
    }

    const innerW = W - PAD.l - PAD.r;
    const innerH = H - PAD.t - PAD.b;
    const gap = 3;
    const bw = Math.max(2, (innerW - gap * (data.length - 1)) / data.length);
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const start = performance.now();
    const DUR = reduce ? 0 : 900;

    function frame(now) {
        const p = DUR ? Math.min(1, (now - start) / DUR) : 1;
        const eased = 1 - Math.pow(1 - p, 3);
        ctx.clearRect(0, 0, W, H);

        // hairline gridlines at 25/50/75/100
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.lineWidth = 1;
        [0, 0.25, 0.5, 0.75, 1].forEach(f => {
            const y = PAD.t + innerH * f;
            ctx.beginPath();
            ctx.moveTo(PAD.l, y + 0.5);
            ctx.lineTo(W - PAD.r, y + 0.5);
            ctx.stroke();
        });

        data.forEach((l, i) => {
            const cat = (l.category || 'Cold').toLowerCase();
            const score = Number(l.score) || 0;
            const h = (score / 100) * innerH * eased;
            const x = PAD.l + i * (bw + gap);
            const y = PAD.t + innerH - h;
            ctx.fillStyle = COLOR[cat] || COLOR.cold;
            ctx.globalAlpha = 0.9;
            ctx.fillRect(x, y, bw, h);
            // cap highlight
            ctx.globalAlpha = 1;
            ctx.fillRect(x, y, bw, Math.min(2, h));
        });

        // trend line across the tops
        ctx.globalAlpha = 1;
        ctx.strokeStyle = 'rgba(255,176,32,0.55)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        data.forEach((l, i) => {
            const x = PAD.l + i * (bw + gap) + bw / 2;
            const y = PAD.t + innerH - ((Number(l.score) || 0) / 100) * innerH * eased;
            i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
        });
        ctx.stroke();

        if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
}

// ── Ticker tape ─────────────────────────────────────────────────────────────────
function buildTicker(leads) {
    const track = document.getElementById('tickerTrack');
    if (!track || !leads.length) return;
    const item = (l) => {
        const cat = (l.category || 'Cold').toLowerCase();
        const up = (Number(l.interest) || 0) >= 7;
        return `<span class="tick ${cat}">
            <b>${escapeHtml(l.company || '—')}</b>
            <span class="t-score">${escapeHtml(l.score)}</span>
            <span class="t-arrow ${up ? 'up' : 'down'}">${up ? '▲' : '▼'}</span>
            <span>${escapeHtml(l.category)}</span>
        </span>`;
    };
    // Duplicated once so the -50% scroll loops seamlessly.
    const row = leads.map(item).join('');
    track.innerHTML = row + row;
}

// ── Scroll reveal ───────────────────────────────────────────────────────────────
// Cards animate as they enter the viewport instead of all firing on load.
function initScrollReveal() {
    const targets = document.querySelectorAll('.card, .kpi-card, .board-main, .board-side, .dash-card');
    if (!('IntersectionObserver' in window) || !targets.length) return;
    const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('in');
                io.unobserve(e.target);
            }
        });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    targets.forEach(t => { t.classList.add('will-reveal'); io.observe(t); });
}

// ── Boot sequence ───────────────────────────────────────────────────────────────
// A short cold-start once per browser session. Skippable by any key or click.
const BOOT_KEY = 'salesspark_booted';

function runBoot() {
    if (sessionStorage.getItem(BOOT_KEY)) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    sessionStorage.setItem(BOOT_KEY, '1');

    const lines = [
        'SALESSPARK TERMINAL v4.0',
        'connecting to pipeline…',
        'loading lead book…',
        'copilot online',
    ];
    const el = document.createElement('div');
    el.className = 'boot';
    el.innerHTML = `<div class="boot-inner"><pre id="bootLines"></pre><span class="boot-skip">press any key to skip</span></div>`;
    document.body.appendChild(el);

    const pre = el.querySelector('#bootLines');
    let i = 0;
    const tick = setInterval(() => {
        if (i >= lines.length) return finish();
        pre.textContent += (i ? '\n' : '') + '> ' + lines[i++];
    }, 170);

    function finish() {
        clearInterval(tick);
        el.classList.add('out');
        setTimeout(() => el.remove(), 380);
        window.removeEventListener('keydown', finish);
        window.removeEventListener('click', finish);
    }
    setTimeout(finish, 1000);
    window.addEventListener('keydown', finish);
    window.addEventListener('click', finish);
}

// ── Initialization ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    runBoot();
    initAtmosphere();
    highlightActiveNav();
    initChatbot();
    loadStatusStrip();
    loadBoard();
    initScrollReveal();
});

// ── Chatbot widget ──────────────────────────────────────────────────────────────
function welcomeHtml() {
    return `
        <div class="chat-message bot">
            <div class="message-content">
                <div class="bot-avatar">🤖</div>
                <div class="msg-col"><div class="bubble">
                    <strong>SalesSpark Copilot</strong> online.<br>
                    I can score leads, plan deals, draft outreach, and take you anywhere in the app.<br><br>
                    <em>Type <code>/</code> for commands, or try one below ↓</em>
                </div></div>
            </div>
        </div>
        <div class="chat-suggestions" id="chatSuggestions">
            <div class="suggestion-chip" onclick="sendSuggestion(this)">Which leads are hot?</div>
            <div class="suggestion-chip" onclick="sendSuggestion(this)">How is my pipeline?</div>
            <div class="suggestion-chip" onclick="sendSuggestion(this)">What should I do next?</div>
            <div class="suggestion-chip" onclick="sendSuggestion(this)">Show my leads</div>
        </div>`;
}

function initChatbot() {
    const chatHTML = `
        <div class="chatbot-widget">
            <button class="chat-toggle-btn" onclick="toggleChat()" title="SalesSparkAI Copilot (Ctrl+K)" aria-label="Open SalesSparkAI Copilot">
                <span class="chat-icon"></span>
                <span class="chat-pulse"></span>
                <span class="chat-badge" id="chatBadge" style="display:none;" aria-hidden="true"></span>
            </button>
            <div class="chat-window" id="chatWindow" role="dialog" aria-label="SalesSparkAI Copilot">
                <div class="chat-header">
                    <div class="header-info">
                        <h3>SalesSpark AI</h3>
                        <span class="header-subtitle">Your sales intelligence copilot</span>
                    </div>
                    <div class="chat-header-actions">
                        <button class="chat-icon-btn" onclick="clearChat()" title="Clear conversation" aria-label="Clear conversation">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                        <button class="chat-icon-btn" onclick="toggleChat()" title="Close" aria-label="Close">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="chat-divider"></div>
                <div class="chat-body" id="chatBody" role="log" aria-live="polite">${welcomeHtml()}</div>
                <div class="chat-footer">
                    <div class="slash-menu" id="slashMenu" style="display:none;" role="listbox"></div>
                    <div class="input-wrapper">
                        <input type="text" id="chatInput" class="chat-input"
                            placeholder="Ask anything, or type / for commands"
                            aria-label="Message SalesSparkAI Copilot"
                            onkeydown="handleChatKey(event)" oninput="handleChatInput()" autocomplete="off">
                        <button class="chat-mic-btn" id="chatMic" onclick="startVoice()" title="Voice input" aria-label="Voice input">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                                <line x1="12" y1="19" x2="12" y2="23"></line>
                            </svg>
                        </button>
                        <button class="chat-send-btn" id="chatSend" onclick="sendChatMessage()" title="Send" aria-label="Send">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                        <button class="chat-stop-btn" id="chatStop" onclick="stopGenerating()" title="Stop generating" aria-label="Stop generating" style="display:none;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    document.body.insertAdjacentHTML('beforeend', chatHTML);

    // Hide the mic button if the browser has no speech recognition.
    if (!(window.SpeechRecognition || window.webkitSpeechRecognition)) {
        const mic = document.getElementById('chatMic');
        if (mic) mic.style.display = 'none';
    }

    restoreChat();
    loadBriefing();
    if (localStorage.getItem(CHAT_KEYS.open) === '1') openChat();
}

// ── Proactive briefing ──────────────────────────────────────────────────────────
// On load we quietly check the pipeline. If anything needs attention, the chat
// button gets a badge; opening the copilot delivers the briefing once per day.
let pendingBriefing = null;

function briefingSeenToday() {
    return localStorage.getItem(CHAT_KEYS.briefing) === new Date().toDateString();
}

async function loadBriefing() {
    if (briefingSeenToday()) return;
    try {
        const [alertsRes, actionsRes] = await Promise.all([
            fetch(`${API_BASE}/alerts`),
            fetch(`${API_BASE}/actions/next`),
        ]);
        if (!alertsRes.ok || !actionsRes.ok) return;
        const alerts = (await alertsRes.json()).alerts || [];
        const actions = (await actionsRes.json()).actions || [];
        if (!alerts.length && !actions.length) return;

        const parts = [];
        if (actions.length) {
            const top = actions.slice(0, 3)
                .map(a => `• <strong>${escapeHtml(a.company || 'Lead')}</strong> — ${escapeHtml(a.action || '')}`)
                .join('<br>');
            parts.push(`<strong>${actions.length} lead${actions.length === 1 ? '' : 's'} need attention today</strong><br>${top}`);
        }
        if (alerts.length) {
            parts.push(alerts.slice(0, 2)
                .map(a => `<strong>Alert:</strong> ${escapeHtml(a.message || '')}`)
                .join('<br>'));
        }
        pendingBriefing = parts.join('<br><br>') + '<br><br><em>Want me to draft outreach for the top one?</em>';

        // The fetch above is slower than initChatbot, so a chat that was restored
        // already-open has passed its delivery check by now. Deliver straight into
        // the open panel; only badge it if the user hasn't opened the copilot.
        const win = document.getElementById('chatWindow');
        if (win && win.classList.contains('open')) {
            deliverBriefing();
        } else {
            showBadge(actions.length || alerts.length);
        }
    } catch (e) {
        /* backend down — stay quiet, the widget still works */
    }
}

function showBadge(n) {
    const badge = document.getElementById('chatBadge');
    if (!badge || !n) return;
    badge.textContent = n > 9 ? '9+' : String(n);
    badge.style.display = 'flex';
}

function clearBadge() {
    const badge = document.getElementById('chatBadge');
    if (badge) badge.style.display = 'none';
}

function deliverBriefing() {
    if (!pendingBriefing || briefingSeenToday()) return;
    localStorage.setItem(CHAT_KEYS.briefing, new Date().toDateString());
    const html = pendingBriefing;
    pendingBriefing = null;
    clearBadge();
    botInstant(html);
}

function toggleChat() {
    const win = document.getElementById('chatWindow');
    if (win.classList.contains('open')) closeChat(); else openChat();
}
function openChat() {
    const win = document.getElementById('chatWindow');
    const btn = document.querySelector('.chat-toggle-btn');
    win.classList.add('open');
    if (btn) btn.classList.add('active');
    localStorage.setItem(CHAT_KEYS.open, '1');
    clearBadge();
    if (transcript.length) scrollChat(); else scrollChatTop();
    setTimeout(() => { const i = document.getElementById('chatInput'); if (i) i.focus(); }, 300);
    if (pendingBriefing) setTimeout(deliverBriefing, 400);
}
function closeChat() {
    const win = document.getElementById('chatWindow');
    const btn = document.querySelector('.chat-toggle-btn');
    win.classList.remove('open');
    if (btn) btn.classList.remove('active');
    localStorage.setItem(CHAT_KEYS.open, '0');
}

// ── Slash commands ──────────────────────────────────────────────────────────────
// `send: true` fires immediately; otherwise the template lands in the input with
// the first <placeholder> selected so the user just types over it.
const SLASH_COMMANDS = [
    { cmd: '/pipeline', hint: 'Pipeline health', text: 'How is my pipeline?', send: true },
    { cmd: '/leads', hint: 'List your hot leads', text: 'Which leads are hot?', send: true },
    { cmd: '/next', hint: 'Next best actions', text: 'What should I do next?', send: true },
    { cmd: '/campaign', hint: 'Generate a campaign', text: 'Create a campaign for <product> targeting <audience> on LinkedIn.' },
    { cmd: '/email', hint: 'Draft a cold email', text: 'Draft a cold email to <recipient> about <context>.' },
    { cmd: '/pitch', hint: 'Write a sales pitch', text: 'Write a sales pitch for <product> aimed at <audience>.' },
    { cmd: '/social', hint: 'Write a social post', text: 'Write a LinkedIn post about <product>.' },
    { cmd: '/score', hint: 'Score a new lead', text: 'Score a new lead: <company>, budget <50000>, interest <8>.' },
    { cmd: '/close', hint: 'Closing plan for a lead', text: 'How do I close <company>?' },
    { cmd: '/followup', hint: 'Follow-up sequence', text: 'Build a follow-up plan for <company>.' },
    { cmd: '/predict', hint: 'Predict a campaign', text: 'Predict results for a LinkedIn campaign with the goal of Leads.' },
    { cmd: '/market', hint: 'Market intelligence', text: 'What is the market outlook for <industry>?' },
    { cmd: '/clear', hint: 'Clear the conversation', action: clearChat },
    { cmd: '/help', hint: 'Show what I can do', action: showSlashHelp },
];

let slashMatches = [];
let slashIndex = 0;

function slashQuery() {
    const input = document.getElementById('chatInput');
    const v = input ? input.value : '';
    return /^\/[a-z]*$/i.test(v.trim()) ? v.trim().toLowerCase() : null;
}

function handleChatInput() {
    const q = slashQuery();
    if (q === null) return closeSlashMenu();
    slashMatches = SLASH_COMMANDS.filter(c => c.cmd.startsWith(q));
    if (!slashMatches.length) return closeSlashMenu();
    slashIndex = 0;
    renderSlashMenu();
}

function renderSlashMenu() {
    const menu = document.getElementById('slashMenu');
    if (!menu) return;
    menu.innerHTML = slashMatches.map((c, i) =>
        `<div class="slash-item${i === slashIndex ? ' active' : ''}" role="option" onmousedown="runSlash(${i})">
            <span class="slash-cmd">${escapeHtml(c.cmd)}</span>
            <span class="slash-hint">${escapeHtml(c.hint)}</span>
        </div>`).join('');
    menu.style.display = 'block';
}

function closeSlashMenu() {
    const menu = document.getElementById('slashMenu');
    if (menu) { menu.style.display = 'none'; menu.innerHTML = ''; }
    slashMatches = [];
}

function runSlash(i) {
    const cmd = slashMatches[i];
    closeSlashMenu();
    if (!cmd) return;
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.value = '';

    if (cmd.action) return cmd.action();
    if (cmd.send) {
        hideSuggestions();
        addUserMessage(cmd.text);
        return handleUserQuery(cmd.text);
    }
    // Prefill and select the first <placeholder> so the user types straight over it.
    input.value = cmd.text;
    input.focus();
    const m = /<[^>]+>/.exec(cmd.text);
    if (m) input.setSelectionRange(m.index, m.index + m[0].length);
}

function showSlashHelp() {
    const lines = SLASH_COMMANDS
        .map(c => `<code>${escapeHtml(c.cmd)}</code> — ${escapeHtml(c.hint)}`)
        .join('<br>');
    botInstant(`<strong>Commands</strong><br>${lines}<br><br><em>Tip: press Ctrl+K anywhere to open me.</em>`);
}

function handleChatKey(e) {
    if (slashMatches.length) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            slashIndex = (slashIndex + 1) % slashMatches.length;
            return renderSlashMenu();
        }
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            slashIndex = (slashIndex - 1 + slashMatches.length) % slashMatches.length;
            return renderSlashMenu();
        }
        if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            return runSlash(slashIndex);
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            return closeSlashMenu();
        }
    }
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    else if (e.key === 'Escape') closeChat();
}

// Ctrl+K / Cmd+K opens the copilot from anywhere in the app.
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const win = document.getElementById('chatWindow');
        if (win && win.classList.contains('open')) {
            const i = document.getElementById('chatInput');
            if (i) i.focus();
        } else {
            openChat();
        }
    }
});

function sendSuggestion(el) {
    const text = el.innerText.replace(/^\p{Extended_Pictographic}️?\s*/u, '').trim();
    hideSuggestions();
    addUserMessage(text);
    handleUserQuery(text);
}

function hideSuggestions() {
    const s = document.getElementById('chatSuggestions');
    if (s) s.remove();
}

function scrollChat() {
    const body = document.getElementById('chatBody');
    if (body) body.scrollTo({ top: body.scrollHeight, behavior: 'smooth' });
}

function scrollChatTop() {
    const body = document.getElementById('chatBody');
    if (body) body.scrollTop = 0;
}

// A reply taller than the panel is pinned to its own first line, so the user
// reads it from the start instead of landing at the end of it.
function keepInView(msgEl) {
    const body = document.getElementById('chatBody');
    if (!body || !msgEl) return;
    if (msgEl.offsetHeight + 28 <= body.clientHeight) {
        body.scrollTop = body.scrollHeight;
        return;
    }
    const top = msgEl.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop;
    body.scrollTop = Math.max(0, top - 12);
}

// ── Message rendering ───────────────────────────────────────────────────────────
function metaEl(sender, ts, isLastBot) {
    const el = document.createElement('div');
    el.className = 'msg-meta';
    const t = new Date(ts || Date.now());
    const hh = ('0' + t.getHours()).slice(-2), mm = ('0' + t.getMinutes()).slice(-2);
    let html = `<span class="msg-time">${hh}:${mm}</span>`;
    if (sender === 'bot') {
        html += `<button class="msg-btn" title="Copy" onclick="copyMessage(this)" aria-label="Copy">⧉</button>`;
        if (isLastBot) html += `<button class="msg-btn regen-btn" title="Regenerate" onclick="regenerateLast()" aria-label="Regenerate">↻</button>`;
    }
    el.innerHTML = html;
    return el;
}

function renderStored(m, isLast) {
    const body = document.getElementById('chatBody');
    if (!body) return null;
    const msg = document.createElement('div');
    msg.className = 'chat-message ' + m.sender;
    const content = document.createElement('div');
    content.className = 'message-content';
    if (m.sender === 'bot') {
        const av = document.createElement('div');
        av.className = 'bot-avatar';
        av.textContent = '';
        content.appendChild(av);
    }
    const col = document.createElement('div');
    col.className = 'msg-col';
    col.innerHTML = m.contentHtml;
    col.appendChild(metaEl(m.sender, m.ts, isLast && m.sender === 'bot'));
    content.appendChild(col);
    msg.appendChild(content);
    body.appendChild(msg);
    return msg;
}

function pushMessage(sender, contentHtml, persist = true) {
    // Only the most recent bot message keeps a regenerate button.
    document.querySelectorAll('#chatBody .regen-btn').forEach(b => b.remove());
    const ts = Date.now();
    const el = renderStored({ sender, contentHtml, ts }, true);
    if (persist) { transcript.push({ sender, contentHtml, ts }); saveTranscript(); }
    if (sender === 'bot') keepInView(el); else scrollChat();
    return el;
}

function addUserMessage(text) {
    pushMessage('user', `<div class="bubble">${escapeHtml(text)}</div>`);
    addToHistory('user', text);
}

function botInstant(html) {
    pushMessage('bot', `<div class="bubble">${html}</div>`);
    addToHistory('assistant', stripHtml(html));
}

function navInstant(nav) {
    const html = `<div class="bubble"><span style="margin-right:6px;">🔗</span>Opening <strong>${escapeHtml(nav.label)}</strong>…</div>`;
    pushMessage('bot', html);
    addToHistory('assistant', 'Opening ' + nav.label);
    setTimeout(() => { window.location.href = nav.url; }, 1000);
}

function restoreChat() {
    const body = document.getElementById('chatBody');
    if (!body || !transcript.length) return;   // keep the default welcome
    body.innerHTML = '';
    let last = null;
    transcript.forEach((m, i) => { last = renderStored(m, i === transcript.length - 1); });
    keepInView(last);
}

// ── Send + route ────────────────────────────────────────────────────────────────
function sendChatMessage() {
    const input = document.getElementById('chatInput');
    if (!input) return;
    const msg = (input.value || '').trim();
    if (!msg || isStreaming) return;

    // A bare "/command" runs the command rather than being sent to the agent.
    const exact = SLASH_COMMANDS.find(c => c.cmd === msg.toLowerCase());
    if (exact) {
        slashMatches = [exact];
        return runSlash(0);
    }

    input.value = '';
    hideSuggestions();
    addUserMessage(msg);
    handleUserQuery(msg);
}

function handleUserQuery(msg) {
    if (isGreeting(msg)) return botInstant(INSTANT_GREETING);
    if (isProductQuestion(msg)) return botInstant(INSTANT_PRODUCT);
    const nav = detectNavigationIntent(msg);
    if (nav) return navInstant(nav);
    const guidance = detectFeatureGuidance(msg, getCurrentPage());
    if (guidance) return botInstant(guidance);
    return streamBotResponse(msg);
}

// ── Streaming agent response ────────────────────────────────────────────────────
function setStreamingUI(on) {
    isStreaming = on;
    const send = document.getElementById('chatSend');
    const stop = document.getElementById('chatStop');
    if (send) send.style.display = on ? 'none' : 'flex';
    if (stop) stop.style.display = on ? 'flex' : 'none';
}

function createStreamingBubble() {
    const body = document.getElementById('chatBody');
    const msg = document.createElement('div');
    msg.className = 'chat-message bot';
    msg.innerHTML =
        '<div class="message-content"><div class="bot-avatar"></div>' +
        '<div class="msg-col"><div class="bubble"><span class="stream-status">Thinking…</span></div>' +
        '<div class="tool-cards"></div></div></div>';
    body.appendChild(msg);
    scrollChat();
    return {
        msgEl: msg,
        bubbleEl: msg.querySelector('.bubble'),
        cardsEl: msg.querySelector('.tool-cards'),
        colEl: msg.querySelector('.msg-col'),
    };
}

async function streamBotResponse(msg) {
    setStreamingUI(true);
    document.querySelectorAll('#chatBody .regen-btn').forEach(b => b.remove());
    const s = createStreamingBubble();
    streamController = new AbortController();

    let acc = '';
    let firstToken = true;
    let toolCards = [];
    let navAction = null;
    let suggestions = null;
    // Tracks whether the server got far enough to run a tool. Tools write to the
    // database (score_lead inserts a lead, generate_campaign inserts a campaign),
    // so retrying a turn that already reached one would run it a second time.
    let toolStarted = false;

    const setStatus = (label) => {
        s.bubbleEl.innerHTML = `<span class="stream-status">${escapeHtml(label)}…</span>`;
    };

    try {
        const res = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg, session_id: CHAT_SESSION_ID,
                current_page: getCurrentPage(), history: priorHistory(),
            }),
            signal: streamController.signal,
        });
        if (!res.ok || !res.body) throw new Error('stream-unavailable');

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let done = false;

        while (!done) {
            const chunk = await reader.read();
            if (chunk.done) break;
            buffer += decoder.decode(chunk.value, { stream: true });
            let idx;
            while ((idx = buffer.indexOf('\n\n')) >= 0) {
                const line = buffer.slice(0, idx).trim();
                buffer = buffer.slice(idx + 2);
                if (!line.startsWith('data:')) continue;
                let ev;
                try { ev = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }

                if (ev.type === 'token') {
                    acc += ev.text || '';
                    firstToken = false;
                    s.bubbleEl.innerHTML = renderRichText(acc) + '<span class="stream-cursor"></span>';
                    keepInView(s.msgEl);
                } else if (ev.type === 'tool') {
                    toolStarted = true;
                    if (firstToken) setStatus(ev.label || 'Working');
                } else if (ev.type === 'tool_result') {
                    toolCards.push(renderToolCard(ev));
                    s.cardsEl.innerHTML = toolCards.join('');
                    keepInView(s.msgEl);
                } else if (ev.type === 'action' && ev.action === 'navigate') {
                    navAction = ev;
                    if (firstToken) setStatus(ev.response || 'Opening');
                } else if (ev.type === 'suggestions') {
                    suggestions = ev.items;
                } else if (ev.type === 'done') {
                    done = true;
                }
            }
        }
    } catch (e) {
        if (e && e.name === 'AbortError') {
            finalizeStream(s, acc, toolCards, null);
            setStreamingUI(false);
            streamController = null;
            return;
        }
        setStreamingUI(false);
        streamController = null;

        // Retrying is only safe if the turn never got as far as running a tool.
        // Once a tool has run its writes are already committed, so re-sending the
        // message would execute it again — a second lead, a second campaign.
        if (!toolStarted && firstToken && !navAction) {
            s.msgEl.remove();
            return fallbackChat(msg);
        }

        // Otherwise keep whatever the server did send and say the rest was lost,
        // rather than silently re-running the work.
        const partial = acc.trim();
        finalizeStream(
            s,
            partial ? partial + '\n\n(The connection dropped before I finished.)'
                    : 'The connection dropped while I was working. Anything above was completed — check before retrying, so it does not run twice.',
            toolCards,
            null,
        );
        return;
    }

    const finalText = acc.trim() || (navAction ? (navAction.response || '') : '');
    finalizeStream(s, finalText, toolCards, navAction);
    if (suggestions) updateSuggestions(suggestions);
    setStreamingUI(false);
    streamController = null;
    if (navAction && navAction.url) {
        setTimeout(() => { window.location.href = navAction.url; }, 1200);
    }
}

function finalizeStream(s, text, toolCards, navAction) {
    const bodyHtml = text ? renderRichText(text) : '<em>Done.</em>';
    s.bubbleEl.innerHTML = bodyHtml;
    s.cardsEl.innerHTML = toolCards.join('');
    // Persist the finished message (content = bubble + cards) then add the meta row.
    const contentHtml = s.bubbleEl.outerHTML + (toolCards.length ? s.cardsEl.outerHTML : '');
    const ts = Date.now();
    s.colEl.appendChild(metaEl('bot', ts, true));
    transcript.push({ sender: 'bot', contentHtml, ts });
    saveTranscript();
    addToHistory('assistant', text || (navAction ? navAction.response : '') || 'Done.');
    keepInView(s.msgEl);
}

// ── Non-streaming fallback (POST /chat) ─────────────────────────────────────────
async function fallbackChat(msg) {
    setStreamingUI(true);
    const s = createStreamingBubble();
    s.bubbleEl.innerHTML = '<span class="stream-status">Thinking…</span>';
    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: msg, session_id: CHAT_SESSION_ID,
                current_page: getCurrentPage(), history: priorHistory(),
            }),
        });
        const data = await res.json();
        // /chat returns every tool it ran, so a turn that both navigates and
        // generates an asset keeps its cards instead of dropping them.
        const cards = (Array.isArray(data.tools) ? data.tools : [])
            .map(t => renderToolCard({ tool: t.tool, result: t.result }))
            .filter(Boolean);
        const text = data.error ? `⚠️ ${data.error}` : (data.response || 'Done.');
        finalizeStream(s, text, cards, data.action === 'navigate' ? data : null);
        if (Array.isArray(data.suggestions)) updateSuggestions(data.suggestions);
        if (data.action === 'navigate' && data.url) {
            setTimeout(() => { window.location.href = data.url; }, 1200);
        }
    } catch (e) {
        s.bubbleEl.innerHTML = 'Could not reach SalesSpark Brain. Is the server running?';
        const ts = Date.now();
        s.colEl.appendChild(metaEl('bot', ts, true));
    } finally {
        setStreamingUI(false);
    }
}

// ── Suggestions ─────────────────────────────────────────────────────────────────
function updateSuggestions(items) {
    if (!items || !items.length) return;
    const body = document.getElementById('chatBody');
    if (!body) return;
    let c = document.getElementById('chatSuggestions');
    if (!c) {
        c = document.createElement('div');
        c.className = 'chat-suggestions';
        c.id = 'chatSuggestions';
    }
    c.innerHTML = items.slice(0, 4).map(it =>
        `<div class="suggestion-chip" onclick="sendSuggestion(this)">${escapeHtml(it)}</div>`
    ).join('');
    body.appendChild(c);   // moves it to the bottom
    scrollChat();
}

// ── Polish: copy / regenerate / stop / clear / voice ────────────────────────────
function copyMessage(btn) {
    const msg = btn.closest('.chat-message');
    const bubble = msg && msg.querySelector('.bubble');
    const text = bubble ? (bubble.innerText || bubble.textContent || '') : '';
    if (!text) return;
    const done = () => { const o = btn.textContent; btn.textContent = '✓'; setTimeout(() => btn.textContent = o, 1200); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => {});
    }
}

function regenerateLast() {
    if (isStreaming) return;
    let lastUser = null;
    for (let i = chatHistory.length - 1; i >= 0; i--) {
        if (chatHistory[i].role === 'user') { lastUser = chatHistory[i].content; break; }
    }
    if (!lastUser) return;
    // Drop the previous assistant turn from history, transcript, and the DOM.
    if (chatHistory.length && chatHistory[chatHistory.length - 1].role === 'assistant') {
        chatHistory.pop(); saveHistory();
    }
    if (transcript.length && transcript[transcript.length - 1].sender === 'bot') {
        transcript.pop(); saveTranscript();
    }
    const bots = document.querySelectorAll('#chatBody .chat-message.bot');
    if (bots.length) bots[bots.length - 1].remove();
    streamBotResponse(lastUser);
}

function stopGenerating() {
    if (streamController) { try { streamController.abort(); } catch (e) {} }
}

function clearChat() {
    if (isStreaming && streamController) { try { streamController.abort(); } catch (e) {} }
    transcript = [];
    chatHistory = [];
    localStorage.removeItem(CHAT_KEYS.transcript);
    localStorage.removeItem(CHAT_KEYS.history);
    const body = document.getElementById('chatBody');
    if (body) body.innerHTML = welcomeHtml();
    scrollChatTop();
}

function startVoice() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    const mic = document.getElementById('chatMic');
    try {
        const rec = new SR();
        rec.lang = 'en-US';
        rec.interimResults = false;
        rec.maxAlternatives = 1;
        if (mic) mic.classList.add('listening');
        rec.onresult = (e) => {
            const t = e.results[0][0].transcript;
            const inp = document.getElementById('chatInput');
            if (inp) { inp.value = t; inp.focus(); }
        };
        rec.onerror = () => { if (mic) mic.classList.remove('listening'); };
        rec.onend = () => { if (mic) mic.classList.remove('listening'); };
        rec.start();
    } catch (e) {
        if (mic) mic.classList.remove('listening');
    }
}
