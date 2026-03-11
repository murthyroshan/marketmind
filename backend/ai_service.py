"""
ai_service.py
-------------
AI service layer for SalesSparkAI Copilot.
Handles all Groq API communication with context-aware, token-optimized prompts.

Architecture:
  routes (main.py) → build_chat_context() → generate_chat_response() → Groq API
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict
from dotenv import load_dotenv

# ── Load .env first, before any os.getenv call ────────────────────────────────
load_dotenv()

logger = logging.getLogger("saleskpark.ai")
logging.basicConfig(level=logging.INFO)

# ── Groq client singleton ──────────────────────────────────────────────────────
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False
    logger.error("[ai_service] groq package missing. Run: pip install groq python-dotenv")

_groq_client: Optional[object] = None
_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if _GROQ_API_KEY and _groq_available:
    try:
        _groq_client = Groq(api_key=_GROQ_API_KEY)
        logger.info("[ai_service] Groq client ready. Key: %s...", _GROQ_API_KEY[:8])
    except Exception as e:
        logger.error("[ai_service] Groq client init failed: %s", e)
else:
    logger.error("[ai_service] GROQ_API_KEY not set or groq not installed.")


# ── Page → URL map (used in navigation responses) ─────────────────────────────
PAGE_URL_MAP: Dict[str, str] = {
    "home":        "/index.html",
    "landing":     "/index.html",
    "index":       "/index.html",
    "dashboard":   "/sales_copilot.html",
    "copilot":     "/sales_copilot.html",
    "sales_copilot":"/sales_copilot.html",
    "leads":       "/leads.html",
    "tools":       "/tools.html",
    "campaigns":   "/tools.html",
    "pitch":       "/tools.html",
    "email":       "/tools.html",
    "social":      "/tools.html",
    "market":      "/market_intelligence.html",
    "prediction":  "/prediction.html",
    "deal-tools":  "/leads.html#deal-tools",
}

# ── Greeting intent detection (zero-token shortcut) ───────────────────────────
_GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|good\s*morning|good\s*afternoon|good\s*evening|howdy|sup|what'?s\s*up|yo)\s*[.!?]?\s*$",
    re.IGNORECASE,
)

_GREETING_RESPONSE = (
    "👋 Hello! I'm <strong>SalesSparkAI Copilot</strong> — your AI sales intelligence assistant.<br><br>"
    "Here's what I can help you with:<br>"
    "• 🔥 <strong>Analyze leads</strong> — find your hottest prospects<br>"
    "• 🚀 <strong>Launch campaigns</strong> — generate targeted strategies<br>"
    "• 🗺️ <strong>Navigate the platform</strong> — just say \"Show my leads\" or \"Open campaigns\"<br>"
    "• 📊 <strong>Pipeline health</strong> — get a real-time sales overview<br><br>"
    "<em>What would you like to explore today?</em>"
)


def _is_greeting(message: str) -> bool:
    """Returns True if the message is a pure greeting — no AI call needed."""
    return bool(_GREETING_PATTERN.match(message.strip()))


# ── Product question detection (zero-token shortcut) ──────────────────────────
_PRODUCT_Q_PATTERN = re.compile(
    r"^\s*(what\s+(is|are|does)\s+(this|the|sales\s*spark|salессhark)?\s*(website|platform|tool|app|product|system|software|it|salessparkAI|sales\s*spark\s*ai)[\s?]*)"
    r"|(how\s+does\s+(this|the)?\s*(platform|tool|app|product|website|salessparkAI|sales\s*spark\s*ai)?\s*work[s?]*)"
    r"|(tell\s+me\s+about\s+(this|the)?\s*(platform|tool|salessparkAI|sales\s*spark\s*ai))"
    r"|(what\s+can\s+(you|this\s+platform|salessparkAI|sales\s*spark\s*ai)\s+do[?]*)"
    r"|(what'?s?\s+(this|salessparkAI|sales\s*spark\s*ai)[?]*)",
    re.IGNORECASE,
)

_PRODUCT_RESPONSE = (
    "<strong>SalesSparkAI</strong> is an AI-powered sales enablement platform designed to help "
    "sales teams analyze leads, generate outreach content, and optimize their sales strategy.<br><br>"
    "🧰 <strong>Platform tools include:</strong><br>"
    "• 🤖 <strong>AI Sales Copilot</strong> — real-time pipeline insights &amp; next-best-action guidance<br>"
    "• 🚀 <strong>Campaign Generator</strong> — multi-channel marketing strategies<br>"
    "• 🎯 <strong>Sales Pitch Generator</strong> — persuasive outreach scripts<br>"
    "• 📧 <strong>Email Outreach</strong> — personalized email drafts<br>"
    "• ⚖️ <strong>Lead Scoring</strong> — scores leads 0-100 (Hot / Warm / Cold)<br>"
    "• 📱 <strong>Social Media Generator</strong> — posts and hashtags<br>"
    "• 📊 <strong>Market Intelligence</strong> — demand, competition &amp; opportunity analysis<br>"
    "• 🔒 <strong>Deal Tools</strong> — closure strategies and follow-up plans<br><br>"
    "<em>Want me to open a specific tool or analyze your pipeline?</em>"
)


def _is_product_question(message: str) -> bool:
    """Returns True if the message is a generic product/platform question."""
    return bool(_PRODUCT_Q_PATTERN.match(message.strip()))


# ── System Prompt ──────────────────────────────────────────────────────────────
def _build_system_prompt(pipeline_summary: str, current_page: str) -> str:
    """
    Concise, token-efficient system prompt.
    Embeds a minimal pipeline summary and current page context.
    """
    page_note = (
        f"The user is currently on the '{current_page}' page."
        if current_page and current_page != "unknown"
        else ""
    )

    nav_pages = ", ".join(PAGE_URL_MAP.keys())

    return (
        "You are SalesSparkAI Copilot, the AI assistant for the SalesSparkAI platform.\n\n"

        f"{page_note}\n\n"

        "ABOUT THE PLATFORM:\n"
        "SalesSparkAI is an AI-powered sales enablement platform that helps sales teams "
        "analyze leads, generate outreach content, and optimize sales strategies.\n\n"

        "PLATFORM TOOLS:\n"
        "• AI Sales Copilot – Pipeline insights and next-best-action guidance.\n"
        "• Campaign Generator – Multi-channel marketing strategies.\n"
        "• Sales Pitch Generator – Persuasive outreach scripts.\n"
        "• Email Outreach – Personalized email drafts.\n"
        "• Social Media Generator – Social posts and hashtags.\n"
        "• Lead Scoring – Scores leads 0-100 (Hot ≥80, Warm 55-79, Cold <55).\n"
        "• Market Intelligence – Demand, competition, and opportunity analysis.\n"
        "• Deal Tools – Closure strategies and follow-up plans.\n\n"

        "LIVE PIPELINE SUMMARY (use only when user asks about sales data):\n"
        f"{pipeline_summary}\n\n"

        "BEHAVIOR RULES:\n"
        "1. GREETING (hi/hello/hey): Warmly introduce yourself and list 2-3 things you can help with. "
        "Never mention pipeline numbers in a greeting.\n"
        "2. PRODUCT QUESTIONS (what is this website, what does SalesSparkAI do, how does this work, "
        "what is this platform, tell me about this tool): Explain the platform using ABOUT THE PLATFORM "
        "and PLATFORM TOOLS above. Keep it concise. No pipeline data.\n"
        "3. FEATURE QUESTIONS (what features are available, what can you do): List the PLATFORM TOOLS "
        "with a one-line description each. No pipeline data.\n"
        "4. NAVIGATION REQUEST (show leads, open campaigns, take me to X): Return ONLY "
        f"a JSON object: {{\"response\": \"short message\", \"action\": \"navigate\", \"page\": \"<page_key>\"}}. "
        f"Valid page keys: {nav_pages}. "
        "STRICT RULES: (a) Use ONLY the listed page keys — never invent URLs or page names. "
        "(b) Output ONLY the raw JSON object — no markdown fences, no explanation, no text before or after. "
        "(c) If no valid page key matches, respond with a normal text answer instead.\n"
        "5. SALES ANALYTICS (how many leads, pipeline health, scores, deals, hot leads): "
        "Use LIVE PIPELINE SUMMARY for a data-grounded answer. Always end with one concrete next-step.\n"
        "6. PAGE-AWARE GUIDANCE (how do I use this, how does X work, guide me): "
        "Tailor your answer to the user's current page. "
        "On 'leads' page → explain lead scores (Hot >=80, Warm 55-79, Cold <55) and the Deal Tools section. "
        "On 'campaigns' page → explain how to fill in the generator form and what outputs to expect. "
        "On 'copilot' page → explain KPI cards, AI Insights panel, and Next Best Actions list. "
        "On 'market' page → explain how to enter an industry and interpret the AI output. "
        "On 'prediction' page → explain the prediction inputs and how to read the result. "
        "Keep guidance to <=80 words and always end with an offer to do something.\n"
        "7. OFF-TOPIC (jokes, coding, recipes, general knowledge, anything unrelated to sales): "
        "Reply with exactly: 'I'm focused on SalesSparkAI features like lead analysis, campaign generation, "
        "and sales strategy. How can I help you with the platform?' — do not deviate from this sentence.\n\n"

        "STYLE: Concise (<=100 words). Warm, confident, direct. "
        "No Markdown headers. Bullets are fine. "
        "For navigation requests output ONLY the raw JSON — no extra text before or after."
    )


# ── Context Builder ────────────────────────────────────────────────────────────
def build_pipeline_summary(db_context: dict) -> str:
    """
    Converts the full db_context dict into a short, token-efficient
    pipeline summary string. Avoids sending raw lead records to the AI.
    """
    total  = db_context.get("total_leads", 0)
    hot    = db_context.get("hot_leads", 0)
    warm   = db_context.get("warm_leads", 0)
    cold   = db_context.get("cold_leads", 0)
    avg    = db_context.get("avg_score", 0)
    health = db_context.get("pipeline_health", "Unknown")
    camps  = db_context.get("total_campaigns", 0)

    # Only include top lead if present
    top_lead_line = ""
    top_leads = db_context.get("top_leads", [])
    if top_leads:
        t = top_leads[0]
        top_lead_line = f"\nTop Lead: {t['company']} | {t['category']} | Score: {t['score']}/100"

    return (
        f"Total Leads: {total} | Hot: {hot} | Warm: {warm} | Cold: {cold} | "
        f"Avg Score: {avg}/100 | Health: {health} | Campaigns: {camps}"
        f"{top_lead_line}"
    )


# ── Navigation Response Parser ─────────────────────────────────────────────────
def _parse_navigation(raw: str) -> dict:
    """
    Checks if the AI returned a navigation JSON.
    Returns a dict with action/page keys if valid, otherwise returns the plain text.
    Handles cases where the model wraps JSON in markdown fences.
    """
    stripped = raw.strip()

    # Strip markdown code fences if present (e.g. ```json ... ```)
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped).strip()

    # The AI should emit raw JSON for navigation; detect it
    if stripped.startswith("{") and "action" in stripped:
        try:
            parsed = json.loads(stripped)
            if parsed.get("action") == "navigate" and parsed.get("page"):
                page_key = parsed["page"].lower().strip()
                url = PAGE_URL_MAP.get(page_key)
                if url:
                    return {
                        "response": parsed.get("response", f"Opening {page_key}..."),
                        "action": "navigate",
                        "page": page_key,
                        "url": url,
                    }
        except json.JSONDecodeError:
            pass  # Not valid JSON, treat as plain text
    return {"response": raw}


# ── Public Interface ───────────────────────────────────────────────────────────
def generate_chat_response(
    message: str,
    db_context: dict,
    current_page: str = "unknown",
    history: List[Dict[str, str]] = None,
) -> dict:
    """
    Sends user message + minimal context to Groq and returns a structured dict.

    Args:
        message      : The user's chat message.
        db_context   : Live pipeline metrics from SQLite.
        current_page : The page the user is currently on (sent from frontend).
        history      : Last N conversation turns [{role, content}, ...].

    Returns:
        dict with at minimum {"response": str}.
        Navigation requests include {"action": "navigate", "page": str, "url": str}.

    Raises:
        RuntimeError : If Groq client is unavailable.
        ValueError   : If message is empty.
    """
    clean = (message or "").strip()
    if not clean:
        raise ValueError("Message must not be empty.")

    # ── Zero-token greeting shortcut ──────────────────────────────────────────
    if _is_greeting(clean):
        logger.info("[ai_service] Greeting detected — skipping Groq call.")
        return {"response": _GREETING_RESPONSE}

    # ── Zero-token product question shortcut ──────────────────────────────────
    if _is_product_question(clean):
        logger.info("[ai_service] Product question detected — skipping Groq call.")
        return {"response": _PRODUCT_RESPONSE}

    if not _groq_client:
        missing = "GROQ_API_KEY not set" if not _GROQ_API_KEY else "groq package missing"
        raise RuntimeError(f"Groq client not initialized: {missing}")

    # Build token-efficient inputs
    pipeline_summary = build_pipeline_summary(db_context)
    system_prompt    = _build_system_prompt(pipeline_summary, current_page)

    # Keep only last 3 history turns (token optimization)
    trimmed_history: List[Dict[str, str]] = []
    if history:
        for turn in history[-6:]:   # last 6 entries = 3 user + 3 assistant
            role = turn.get("role", "").strip()
            content = turn.get("content", "").strip()
            if role in ("user", "assistant") and content:
                trimmed_history.append({"role": role, "content": content})

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": clean})

    logger.info(
        "[ai_service] Groq request | page=%s | history_turns=%d | msg='%s...'",
        current_page, len(trimmed_history), clean[:60],
    )

    completion = _groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.45,
        max_tokens=280,
        stream=False,
    )

    raw_reply = completion.choices[0].message.content.strip()
    logger.info("[ai_service] Groq reply (%d chars): %s...", len(raw_reply), raw_reply[:80])

    return _parse_navigation(raw_reply)


