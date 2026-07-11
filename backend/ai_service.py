"""
ai_service.py
-------------
AI agent layer for the SalesSparkAI Copilot.

Provides a streaming, tool-calling agent built on Groq. Orchestration is
model-driven: the LLM decides when to call a tool, and the caller (main.py)
supplies a ``tool_executor`` callback that runs the real platform action. This
module never imports main.py, so there is no circular dependency.

    main.py  ──build_messages()──►  stream_agent(messages, tool_executor)
                                         │  yields UI events (tokens, tool
                                         │  results, navigate actions)
                                         ▼
                                     Groq API (streaming + function calling)
"""

import os
import json
import logging
from typing import Callable, Dict, Iterator, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("salesspark.ai")

MODEL = "llama-3.3-70b-versatile"

# ── Groq client singleton ──────────────────────────────────────────────────────
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    _groq_available = False
    Groq = None
    logger.error("[ai_service] groq package missing. Run: pip install groq python-dotenv")

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
_groq_client = None
if _GROQ_API_KEY and _groq_available:
    try:
        _groq_client = Groq(api_key=_GROQ_API_KEY)
        logger.info("[ai_service] Groq client ready.")
    except Exception as e:  # pragma: no cover - depends on network/env
        logger.error("[ai_service] Groq client init failed: %s", e)
else:
    logger.error("[ai_service] GROQ_API_KEY not set or groq not installed.")


def groq_ready() -> bool:
    """True when the Groq client is initialized and usable."""
    return _groq_client is not None


# ── Navigation page keys (shared with the navigate_to_page tool) ───────────────
PAGE_KEYS = ["home", "sales_copilot", "leads", "tools", "market", "prediction"]


# ── Tool schemas (Groq function calling) ───────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate_to_page",
            "description": (
                "Open an app page. ONLY when the user explicitly asks to go to/open/show a PAGE. "
                "Never to answer a data question — answer those in chat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "string", "enum": PAGE_KEYS, "description": "Which page to open."}
                },
                "required": ["page"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_pipeline",
            "description": (
                "LIVE pipeline snapshot: lead counts by category, average score, health, top lead. "
                "Always call before answering any question about the user's numbers."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_actions",
            "description": "Get a prioritized list of the next best sales actions based on the user's current leads.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_campaign",
            "description": "Generate a multi-channel marketing campaign strategy for a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "The product or service to promote."},
                    "audience": {"type": "string", "description": "Target audience."},
                    "platform": {"type": "string", "description": "Channel, e.g. LinkedIn, Instagram, Email."},
                    "goal": {"type": "string", "description": "Objective, e.g. Leads, Awareness, Sales."},
                },
                "required": ["product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Write a personalized sales outreach email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Who the email is addressed to."},
                    "product": {"type": "string"},
                    "context": {"type": "string", "description": "The situation or pain point the email addresses."},
                },
                "required": ["recipient", "product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pitch",
            "description": "Generate a persuasive sales pitch for a product and target buyer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string"},
                    "target": {"type": "string", "description": "The target buyer or segment."},
                },
                "required": ["product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_intelligence",
            "description": "Analyze market demand, competition, and opportunity for an industry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "e.g. saas, fintech, healthcare, retail."},
                    "region": {"type": "string", "description": "Region to analyze, e.g. Global, North America, Europe."},
                    "time_horizon": {"type": "string", "description": "Short, Mid, or Long."},
                },
                "required": ["industry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_leads",
            "description": (
                "List the user's actual leads by name and score. Use when they ask which leads "
                "are hot/warm/cold, who to call, or to name specific accounts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["Hot", "Warm", "Cold"], "description": "Filter by category. Omit for all."},
                    "limit": {"type": "integer", "description": "How many to return (max 10)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_lead",
            "description": (
                "Score and save a NEW lead (0-100, Hot/Warm/Cold). Needs company, budget in "
                "dollars, and interest 1-10. If any are missing, ask the user first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "budget": {"type": "integer", "description": "Annual budget in dollars."},
                    "interest": {"type": "integer", "description": "Interest level, 1-10."},
                    "industry": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["company", "budget", "interest"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_deal_strategy",
            "description": "Build a closing strategy for an EXISTING lead: how to close it, discount range, objections, next step.",
            "parameters": {
                "type": "object",
                "properties": {"company": {"type": "string", "description": "Company name or lead id."}},
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_followup_plan",
            "description": "Build a day 1 / day 3 / day 7 follow-up sequence for an EXISTING lead.",
            "parameters": {
                "type": "object",
                "properties": {"company": {"type": "string", "description": "Company name or lead id."}},
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_campaign",
            "description": "Predict engagement and conversion for a campaign before it launches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "description": "LinkedIn, Email, Instagram, Twitter…"},
                    "goal": {"type": "string", "description": "Leads, Awareness, Sales, Engagement…"},
                },
                "required": ["platform", "goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_social",
            "description": "Write a social media post (with hashtags) for a product on a platform.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string"},
                    "platform": {"type": "string", "description": "LinkedIn, Instagram, Twitter…"},
                },
                "required": ["product", "platform"],
            },
        },
    },
]

# Human-friendly status labels shown while a tool runs.
TOOL_LABELS = {
    "navigate_to_page": "Opening page",
    "analyze_pipeline": "Analyzing your pipeline",
    "get_next_actions": "Finding next best actions",
    "generate_campaign": "Creating campaign",
    "draft_email": "Drafting email",
    "generate_pitch": "Writing pitch",
    "get_market_intelligence": "Analyzing market",
    "list_leads": "Pulling your leads",
    "score_lead": "Scoring lead",
    "get_deal_strategy": "Building closing plan",
    "get_followup_plan": "Planning follow-ups",
    "predict_campaign": "Running prediction",
    "generate_social": "Writing social post",
}


# ── Context builder ────────────────────────────────────────────────────────────
def build_pipeline_summary(db_context: dict) -> str:
    """Compress the pipeline snapshot into a short, token-efficient summary."""
    total = db_context.get("total_leads", 0)
    hot = db_context.get("hot_leads", 0)
    warm = db_context.get("warm_leads", 0)
    cold = db_context.get("cold_leads", 0)
    avg = db_context.get("avg_score", 0)
    health = db_context.get("pipeline_health", "Unknown")
    camps = db_context.get("total_campaigns", 0)

    top_lead_line = ""
    top_leads = db_context.get("top_leads", [])
    if top_leads:
        t = top_leads[0]
        top_lead_line = f" | Top Lead: {t.get('company')} ({t.get('category')}, {t.get('score')}/100)"

    return (
        f"Total Leads: {total} | Hot: {hot} | Warm: {warm} | Cold: {cold} | "
        f"Avg Score: {avg}/100 | Health: {health} | Campaigns: {camps}{top_lead_line}"
    )


# ── System prompt ──────────────────────────────────────────────────────────────
def build_system_prompt(pipeline_summary: str, current_page: str) -> str:
    page_note = (
        f"The user is currently on the '{current_page}' page."
        if current_page and current_page not in ("", "unknown")
        else ""
    )
    return (
        "You are SalesSparkAI Copilot, an elite AI sales assistant embedded in the SalesSparkAI "
        "platform. You help sales teams analyze leads, generate outreach (campaigns, emails, pitches, "
        "social posts), run market and campaign analysis, and prioritize deals.\n"
        f"{page_note}\n\n"
        "TOOLS — you can take real actions. Use them proactively instead of guessing:\n"
        "- ANY question about the user's pipeline, scores, or health -> call analyze_pipeline "
        "FIRST, then answer using the real numbers it returns.\n"
        "- Which leads are hot / name my leads / who should I call -> list_leads.\n"
        "- 'what should I do next' / priorities -> get_next_actions.\n"
        "- Add or score a NEW lead -> score_lead (ask for company, budget, and interest 1-10 if missing).\n"
        "- How do I close / negotiate a specific account -> get_deal_strategy.\n"
        "- Follow-up sequence or cadence for an account -> get_followup_plan.\n"
        "- Will this campaign work / predict results -> predict_campaign.\n"
        "- Create a campaign, email, pitch, social post, or market analysis -> the matching tool.\n"
        "- navigate_to_page ONLY when the user explicitly asks to open/go to/show a PAGE "
        "('show my leads', 'open the tools page'). A QUESTION is never a navigation request: "
        "'how is my pipeline?', 'which leads are hot?', 'what should I do next?' are answered "
        "in the chat with data — never by navigating the user away. When in doubt, answer, don't navigate.\n"
        "Never invent pipeline numbers, lead names, or scores — always get them from a tool.\n\n"
        f"CURRENT CONTEXT (may be stale; prefer analyze_pipeline): {pipeline_summary}\n\n"
        "STYLE: Professional, warm, and SHORT — 2-4 sentences (<=60 words). This is a small chat "
        "window, so long answers get scrolled away. Lead with the answer, skip preamble, use at most 3 "
        "tight bullets, and close with one concrete next step or question. When a tool already "
        "returns a generated asset (campaign, email, pitch), the UI renders it as a card — just "
        "introduce it in one line, do not repeat its contents. If a request is off-topic, briefly "
        "steer back to their sales work.\n"
        "Speak naturally — never output raw JSON, code fences, or tool syntax; the tools handle actions."
    )


def build_messages(
    message: str,
    pipeline_summary: str,
    current_page: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Dict]:
    """Assemble the Groq message list from system prompt + trimmed history + user turn."""
    messages: List[Dict] = [
        {"role": "system", "content": build_system_prompt(pipeline_summary, current_page)}
    ]
    if history:
        for turn in history[-8:]:  # last 8 turns keeps context without bloating tokens
            role = (turn.get("role") or "").strip()
            content = (turn.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


# ── Streaming, tool-calling agent loop ─────────────────────────────────────────
def stream_agent(
    messages: List[Dict],
    tool_executor: Callable[[str, dict], dict],
    max_rounds: int = 4,
) -> Iterator[dict]:
    """
    Run the agent, yielding UI events as they happen:

      {"type": "token", "text": "..."}                     streamed answer text
      {"type": "tool", "phase": "start", "name", "label"}  a tool is running
      {"type": "tool_result", "tool", "result"}            rich result to render
      {"type": "action", "action": "navigate", ...}        client should navigate

    ``tool_executor(name, args)`` must return
    ``{"for_model": str, "event": dict | None}``.
    """
    # "unavailable" tells the caller the model never answered, so it can fall back
    # to the deterministic path. It is only safe to emit while nothing has been
    # streamed and no tool has run — replaying a turn that already executed a
    # writing tool would run it twice.
    if _groq_client is None:
        yield {"type": "unavailable", "reason": "unconfigured"}
        return

    tool_ran = False

    for _round in range(max_rounds):
        content_parts: List[str] = []
        tool_calls: Dict[int, Dict[str, str]] = {}
        streamed_any = False

        # The whole round (create + iteration) is guarded: Groq can raise mid-stream
        # (e.g. a transient "failed to call a function" tool-validation error), and we
        # must degrade gracefully rather than propagate.
        try:
            stream = _groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.4,
                max_tokens=400,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    content_parts.append(delta.content)
                    streamed_any = True
                    yield {"type": "token", "text": delta.content}
                for tc in (getattr(delta, "tool_calls", None) or []):
                    slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments
        except Exception as exc:  # network / rate-limit / transient Groq tool-call errors
            logger.error("[ai_service] stream round failed: %s", exc)
            if streamed_any:
                return
            if not tool_ran:
                rate_limited = "rate_limit" in str(exc).lower() or "429" in str(exc)
                yield {"type": "unavailable",
                       "reason": "rate_limit" if rate_limited else "error"}
                return
            # Tools already ran, so we must not replay the turn — but their results are
            # sitting in `messages` and the model died before summarising them. Hand the
            # user the raw result rather than a bare "Done.".
            last = next(
                (m.get("content") for m in reversed(messages)
                 if m.get("role") == "tool" and m.get("content")),
                "",
            )
            yield {
                "type": "token",
                "text": (
                    f"{last}\n\n_The AI ran out of quota before it could summarise this, "
                    "so that's the raw result._"
                    if last else "Sorry, I couldn't complete that just now. Please try again."
                ),
            }
            return

        if not tool_calls:
            return  # model produced a final natural-language answer (already streamed)

        # Record the assistant turn that requested the tools.
        messages.append({
            "role": "assistant",
            "content": "".join(content_parts) or None,
            "tool_calls": [
                {
                    "id": slot["id"] or f"call_{idx}",
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": slot["args"] or "{}"},
                }
                for idx, slot in tool_calls.items()
            ],
        })

        # Execute each requested tool and feed the results back to the model.
        for idx, slot in tool_calls.items():
            name = slot["name"]
            call_id = slot["id"] or f"call_{idx}"
            yield {"type": "tool", "phase": "start", "name": name,
                   "label": TOOL_LABELS.get(name, "Working")}
            try:
                args = json.loads(slot["args"]) if slot["args"].strip() else {}
            except json.JSONDecodeError:
                args = {}
            tool_ran = True
            try:
                outcome = tool_executor(name, args) or {}
            except Exception as exc:
                logger.error("[ai_service] tool '%s' failed: %s", name, exc)
                outcome = {"for_model": f"The {name} action failed. Tell the user briefly.", "event": None}

            event = outcome.get("event")
            if event:
                yield event
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": str(outcome.get("for_model", "")),
            })
        # loop again: the model now answers using the tool results (streamed)

    # Safety valve: exhausted the tool-call budget without a final answer.
    yield {"type": "token", "text": "Here's what I found — let me know if you'd like me to go deeper."}


def run_agent(
    messages: List[Dict],
    tool_executor: Callable[[str, dict], dict],
    max_rounds: int = 4,
) -> dict:
    """Non-streaming wrapper: drain ``stream_agent`` into a single response dict."""
    text_parts: List[str] = []
    action: Optional[dict] = None
    # Every tool the turn ran, not just the last one. A turn can call several
    # (list_leads then draft_email), and it can navigate *and* generate an asset —
    # keeping one, or dropping them all when navigating, silently loses cards the
    # streaming path renders.
    tool_evts: List[dict] = []

    unavailable: Optional[str] = None

    for ev in stream_agent(messages, tool_executor, max_rounds=max_rounds):
        etype = ev.get("type")
        if etype == "token":
            text_parts.append(ev.get("text", ""))
        elif etype == "action":
            action = ev
        elif etype == "tool_result":
            tool_evts.append(ev)
        elif etype == "unavailable":
            unavailable = ev.get("reason") or "error"

    if unavailable:
        return {"unavailable": unavailable}

    response = "".join(text_parts).strip()
    out: dict = {"response": response or "Done."}
    if tool_evts:
        out["tools"] = [
            {"tool": e.get("tool"), "result": e.get("result")} for e in tool_evts
        ]
    if action:
        out["response"] = response or action.get("response") or out["response"]
        out["action"] = "navigate"
        out["page"] = action.get("page")
        out["url"] = action.get("url")
    return out
