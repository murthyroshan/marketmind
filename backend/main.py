from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
import hashlib
import json
import logging
from contextlib import contextmanager
import os
import random
import re
import sqlite3
from typing import Any, Callable, Dict, Iterator, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("salespark")

try:
    from backend.ai_service import (
        build_messages, build_pipeline_summary, stream_agent, run_agent, groq_ready,
        TOOL_LABELS,
    )
except ImportError:
    from ai_service import (
        build_messages, build_pipeline_summary, stream_agent, run_agent, groq_ready,
        TOOL_LABELS,
    )

try:
    from backend.phase2_ai import generate_json
except ImportError:
    from phase2_ai import generate_json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "backend", "sales.db")

app = FastAPI()

# Explicit local dev origins. Wildcard "*" is invalid when credentials are
# allowed (browsers reject it) and would expose authenticated cross-origin calls.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory=os.path.join(PROJECT_ROOT, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(PROJECT_ROOT, "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(PROJECT_ROOT, "assets")), name="assets")

class CampaignRequest(BaseModel):
    product: str
    platform: str
    goal: str
    audience: Optional[str] = ""


class PitchRequest(BaseModel):
    product: str
    target: str


class ScoreRequest(BaseModel):
    company: str = Field(min_length=1)
    budget: int = Field(ge=0)
    interest: int = Field(ge=1, le=10)
    industry: Optional[str] = None
    region: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    deal_stage: Optional[str] = "Prospecting"
    notes: Optional[str] = None


class EmailRequest(BaseModel):
    recipient: str
    context: str
    product: str


class ContentRequest(BaseModel):
    product: str
    platform: str


class PredictionRequest(BaseModel):
    platform: str
    goal: str


class DealAssistRequest(BaseModel):
    lead_id: int


class FollowupRequest(BaseModel):
    lead_id: int


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    current_page: str = "unknown"
    history: list = []


class MarketAnalysisRequest(BaseModel):
    industry: str
    region: str = "Global"
    time_horizon: str = "Mid"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_conn():
    """Yield a DB connection and guarantee it is closed, even on exception."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def ensure_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            audience TEXT,
            platform TEXT,
            goal TEXT,
            objective TEXT,
            theme TEXT,
            marketing_strategy TEXT,
            messaging_approach TEXT,
            cta TEXT,
            expected_outcome TEXT,
            outcome TEXT,
            ai_insight TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            budget INTEGER,
            interest INTEGER,
            score INTEGER,
            category TEXT,
            industry TEXT,
            region TEXT,
            contact_name TEXT,
            contact_email TEXT,
            deal_stage TEXT DEFAULT 'Prospecting',
            last_contacted TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER REFERENCES leads(id),
            action_type TEXT,
            content TEXT,
            scheduled_for TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            output TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(feature, input_hash)
        )
        """
    )

    ensure_column(cur, "campaigns", "audience", "TEXT")
    ensure_column(cur, "campaigns", "objective", "TEXT")
    ensure_column(cur, "campaigns", "theme", "TEXT")
    ensure_column(cur, "campaigns", "marketing_strategy", "TEXT")
    ensure_column(cur, "campaigns", "messaging_approach", "TEXT")
    ensure_column(cur, "campaigns", "cta", "TEXT")
    ensure_column(cur, "campaigns", "expected_outcome", "TEXT")
    ensure_column(cur, "campaigns", "outcome", "TEXT")
    ensure_column(cur, "campaigns", "ai_insight", "TEXT")

    ensure_column(cur, "leads", "industry", "TEXT")
    ensure_column(cur, "leads", "region", "TEXT")
    ensure_column(cur, "leads", "contact_name", "TEXT")
    ensure_column(cur, "leads", "contact_email", "TEXT")
    ensure_column(cur, "leads", "deal_stage", "TEXT DEFAULT 'Prospecting'")
    ensure_column(cur, "leads", "last_contacted", "TIMESTAMP")
    ensure_column(cur, "leads", "notes", "TEXT")

    # Backward-compatible interactions schema migration
    ensure_column(cur, "interactions", "content", "TEXT")
    ensure_column(cur, "interactions", "scheduled_for", "TEXT")
    ensure_column(cur, "interactions", "notes", "TEXT")

    count = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    if count == 0:
        seed_data = [
            ("TechCorp", 90000, 9, 100, "Hot", "SaaS", "North America", "Maya Chen", "maya@techcorp.com", "Proposal", datetime.utcnow() - timedelta(days=1), "Requested enterprise pricing.", datetime.utcnow() - timedelta(days=10)),
            ("BlueSky Inc", 55000, 8, 90, "Hot", "Technology", "Europe", "Owen Park", "owen@bluesky.io", "Demo", datetime.utcnow() - timedelta(days=2), "Strong product fit.", datetime.utcnow() - timedelta(days=8)),
            ("FinCore", 30000, 7, 80, "Hot", "Finance", "North America", "Priya Menon", "priya@fincore.com", "Negotiation", datetime.utcnow() - timedelta(days=1), "Needs compliance summary.", datetime.utcnow() - timedelta(days=6)),
            ("SmartComm", 25000, 7, 70, "Warm", "Telecom", "APAC", "Leo Tan", "leo@smartcomm.com", "Discovery", datetime.utcnow() - timedelta(days=4), "Interested in outbound automation.", datetime.utcnow() - timedelta(days=5)),
            ("EcoEnergy", 18000, 6, 65, "Warm", "Energy", "Europe", "Sara Nordin", "sara@ecoenergy.eu", "Prospecting", datetime.utcnow() - timedelta(days=5), "Early stage but budget approved.", datetime.utcnow() - timedelta(days=4)),
            ("MediCare Plus", 22000, 5, 55, "Warm", "Healthcare", "APAC", "Arjun Das", "arjun@medicareplus.com", "Prospecting", datetime.utcnow() - timedelta(days=7), "Needs case study.", datetime.utcnow() - timedelta(days=3)),
            ("DataFlow", 12000, 5, 50, "Cold", "Analytics", "North America", "Nina Shah", "nina@dataflow.ai", "Nurture", datetime.utcnow() - timedelta(days=12), "Budget cycle next quarter.", datetime.utcnow() - timedelta(days=12)),
            ("EduLearning", 8000, 4, 40, "Cold", "Education", "Europe", "Luca Meyer", "luca@edulearning.com", "Nurture", datetime.utcnow() - timedelta(days=14), "Price sensitive.", datetime.utcnow() - timedelta(days=14)),
        ]
        cur.executemany(
            """
            INSERT INTO leads (
                company, budget, interest, score, category, industry, region,
                contact_name, contact_email, deal_stage, last_contacted, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    company, budget, interest, score, category, industry, region,
                    contact_name, contact_email, deal_stage, last_contacted.isoformat(), notes, created_at.isoformat(),
                )
                for (
                    company, budget, interest, score, category, industry, region,
                    contact_name, contact_email, deal_stage, last_contacted, notes, created_at,
                ) in seed_data
            ],
        )

    conn.commit()
    conn.close()


try:
    init_db()
except Exception as exc:  # startup diagnostics: degrade instead of failing import
    logger.error("[startup] init_db() failed: %s", exc)


INDUSTRY_BASELINES = {
    "saas": {"demand": 78, "competition": 72, "opportunity": 70, "channels": {"LinkedIn": 88, "Email": 75, "Instagram": 38}},
    "finance": {"demand": 68, "competition": 85, "opportunity": 58, "channels": {"LinkedIn": 82, "Email": 86, "Instagram": 24}},
    "technology": {"demand": 74, "competition": 69, "opportunity": 67, "channels": {"LinkedIn": 79, "Email": 68, "Instagram": 45}},
    "healthcare": {"demand": 81, "competition": 58, "opportunity": 76, "channels": {"LinkedIn": 58, "Email": 92, "Instagram": 28}},
    "ecommerce": {"demand": 72, "competition": 77, "opportunity": 60, "channels": {"LinkedIn": 40, "Email": 61, "Instagram": 94}},
}

REGION_MULTIPLIERS = {
    "Global": {"demand": 1.0, "competition": 1.0},
    "North America": {"demand": 1.15, "competition": 1.2},
    "NA": {"demand": 1.15, "competition": 1.2},
    "Europe": {"demand": 1.08, "competition": 1.12},
    "EU": {"demand": 1.08, "competition": 1.12},
    "APAC": {"demand": 1.25, "competition": 1.05},
}

def _lookup_ci(table: Dict[str, Any], key: str, default: Any) -> Any:
    """Case-insensitive dict lookup so 'apac'/'north america' match their keys."""
    if key in table:
        return table[key]
    lowered = key.strip().lower()
    for k, v in table.items():
        if k.lower() == lowered:
            return v
    return default


TIME_MULTIPLIERS = {
    "Short": {"demand": 0.9, "opportunity": 0.82},
    "Mid": {"demand": 1.0, "opportunity": 1.0},
    "Long": {"demand": 1.18, "opportunity": 1.26},
}

def category_for_score(score: int) -> str:
    if score >= 80:
        return "Hot"
    if score >= 55:
        return "Warm"
    return "Cold"


def score_lead_formula(budget: int, interest: int) -> int:
    score = 20
    if budget >= 50000:
        score += 40
    elif budget >= 10000:
        score += 30
    elif budget >= 5000:
        score += 15
    else:
        score += 5

    if interest >= 9:
        score += 40
    elif interest >= 7:
        score += 30
    elif interest >= 5:
        score += 15
    else:
        score += 5

    return min(100, score)


def recommendation_for_category(category: str) -> str:
    if category == "Hot":
        return "Schedule a discovery call within 3 days"
    if category == "Warm":
        return "Send a personalized nurture email with a relevant case study"
    return "Add to monthly newsletter for long-term brand awareness"


def serialize_rows(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def make_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def get_cached_output(feature: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with db_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT output FROM ai_outputs WHERE feature = ? AND input_hash = ?",
            (feature, make_hash(payload)),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["output"])
    except json.JSONDecodeError:
        return None


def save_cached_output(feature: str, payload: Dict[str, Any], data: Dict[str, Any]) -> None:
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_outputs (feature, input_hash, output)
            VALUES (?, ?, ?)
            ON CONFLICT(feature, input_hash) DO UPDATE SET output = excluded.output, created_at = CURRENT_TIMESTAMP
            """,
            (feature, make_hash(payload), json.dumps(data)),
        )
        conn.commit()


def ai_or_fallback(feature: str, payload: Dict[str, Any], system_prompt: str, user_prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    cached = get_cached_output(feature, payload)
    if cached:
        # Merge over the current fallback so a cache row written under an older
        # schema can't cause a KeyError when a new key is accessed downstream.
        return {**fallback, **cached}
    result = generate_json(
        feature=feature,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback=fallback,
    )
    save_cached_output(feature, payload, result)
    return result


def get_pipeline_snapshot() -> Dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor()
        total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        hot_leads = cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80").fetchone()[0]
        warm_leads = cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 55 AND score < 80").fetchone()[0]
        cold_leads = cur.execute("SELECT COUNT(*) FROM leads WHERE score < 55").fetchone()[0]
        avg_raw = cur.execute("SELECT AVG(score) FROM leads").fetchone()[0]
        avg_score = round(avg_raw, 1) if avg_raw is not None else 0.0
        total_campaigns = cur.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        top_rows = cur.execute(
            "SELECT id, company, category, score, budget FROM leads ORDER BY score DESC, created_at DESC LIMIT 5"
        ).fetchall()

    if total_leads == 0:
        health = "Empty"
    elif hot_leads >= 3 and avg_score >= 60:
        health = "Healthy"
    elif hot_leads == 0:
        health = "At Risk"
    else:
        health = "Needs Nurturing"

    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "cold_leads": cold_leads,
        "avg_score": avg_score,
        "total_campaigns": total_campaigns,
        "pipeline_health": health,
        "top_leads": [dict(row) for row in top_rows],
    }


def get_market_context() -> Dict[str, Any]:
    with db_conn() as conn:
        cur = conn.cursor()
        industries = [row[0] for row in cur.execute("SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND TRIM(industry) != '' ORDER BY industry").fetchall()]
        regions = [row[0] for row in cur.execute("SELECT DISTINCT region FROM leads WHERE region IS NOT NULL AND TRIM(region) != '' ORDER BY region").fetchall()]
        products = [row[0] for row in cur.execute("SELECT DISTINCT product FROM campaigns WHERE product IS NOT NULL AND TRIM(product) != '' ORDER BY product").fetchall()]
    return {
        "industries": industries,
        "regions": regions,
        "products": products,
    }


def try_market_search(industry: str, region: str, product: str = "") -> str:
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    serpapi_key = os.getenv("SERPAPI_API_KEY", "").strip()
    query = f"{industry} market demand competition {region} {product}".strip()

    if tavily_key:
        try:
            payload = json.dumps({
                "api_key": tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
            }).encode("utf-8")
            req = Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])[:3]
            if results:
                return " ".join(f"{item.get('title', '')}: {item.get('content', '')}" for item in results)
        except Exception as exc:
            logger.warning("[market] Tavily lookup failed: %s", exc)

    if serpapi_key:
        try:
            params = urlencode({"engine": "google", "q": query, "api_key": serpapi_key})
            with urlopen(f"https://serpapi.com/search.json?{params}", timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            organic = data.get("organic_results", [])[:3]
            if organic:
                return " ".join(f"{item.get('title', '')}: {item.get('snippet', '')}" for item in organic)
        except Exception as exc:
            logger.warning("[market] SerpAPI lookup failed: %s", exc)

    return ""


def build_demand_trend(demand_score: int, horizon: str, avg_score: float) -> List[int]:
    seed = int(demand_score + avg_score)
    # Use a local RNG instance: sync handlers run in a threadpool, so seeding the
    # process-global random would let concurrent requests corrupt each other's output.
    rng = random.Random(seed)
    values = []
    start = max(30, demand_score - 10)
    growth = 3 if horizon == "Short" else 5 if horizon == "Mid" else 7
    for idx in range(6):
        noise = rng.randint(-4, 4)
        values.append(max(0, min(100, start + idx * growth + noise)))
    return values



def normalize_channels(channels: Any, default_channels: Dict[str, int]) -> Dict[str, int]:
    if not isinstance(channels, dict):
        return dict(default_channels)

    normalized = {}
    for key, fallback_val in default_channels.items():
        raw = channels.get(key, fallback_val)
        try:
            val = int(float(raw))
        except (TypeError, ValueError):
            val = fallback_val
        normalized[key] = max(0, min(100, val))
    return normalized

def log_interaction(lead_id: int, action_type: str, content: Dict[str, Any], scheduled_for: Optional[str] = None) -> None:
    conn = get_db()
    cur = conn.cursor()
    try:
        cols = {row[1] for row in cur.execute("PRAGMA table_info(interactions)").fetchall()}
        payload = json.dumps(content)

        if {"content", "scheduled_for"}.issubset(cols):
            cur.execute(
                "INSERT INTO interactions (lead_id, action_type, content, scheduled_for) VALUES (?, ?, ?, ?)",
                (lead_id, action_type, payload, scheduled_for),
            )
        elif "notes" in cols:
            cur.execute(
                "INSERT INTO interactions (lead_id, action_type, notes) VALUES (?, ?, ?)",
                (lead_id, action_type, payload),
            )
        else:
            cur.execute(
                "INSERT INTO interactions (lead_id, action_type) VALUES (?, ?)",
                (lead_id, action_type),
            )

        conn.commit()
    finally:
        conn.close()

@app.post("/campaigns")
def generate_campaign(req: CampaignRequest):
    payload = {
        "product": req.product.strip(),
        "audience": (req.audience or "General buyers").strip(),
        "platform": req.platform.strip(),
        "goal": req.goal.strip(),
    }
    fallback = {
        "theme": f"{payload['product']} growth story for {payload['platform']}",
        "marketing_strategy": f"Use proof-driven {payload['platform']} content tailored to {payload['audience']} and aligned to {payload['goal']}.",
        "messaging_approach": f"Lead with the core business pain, show how {payload['product']} shortens time to value, and close with a low-friction next step.",
        "cta": f"Book a quick strategy call to accelerate {payload['goal'].lower()}.",
        "expected_outcome": f"Improved {payload['goal'].lower()} performance from a more targeted {payload['platform']} campaign.",
        "ai_insight": f"{payload['platform']} audiences respond best when the first message clearly links {payload['product']} to measurable business impact.",
    }
    ai_data = ai_or_fallback(
        "campaign_generator",
        payload,
        "Return only JSON with keys: theme, marketing_strategy, messaging_approach, cta, expected_outcome, ai_insight. Keep each value concise and business-ready.",
        f"Create a campaign for product={payload['product']}, audience={payload['audience']}, platform={payload['platform']}, goal={payload['goal']}.",
        fallback,
    )
    objective = f"Launch a {payload['platform']} campaign for {payload['product']} focused on {payload['goal'].lower()}."
    outcome = ai_data["expected_outcome"]

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO campaigns (
                product, audience, platform, goal, objective, theme,
                marketing_strategy, messaging_approach, cta, expected_outcome,
                outcome, ai_insight, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["product"], payload["audience"], payload["platform"], payload["goal"], objective,
                ai_data["theme"], ai_data["marketing_strategy"], ai_data["messaging_approach"], ai_data["cta"],
                ai_data["expected_outcome"], outcome, ai_data["ai_insight"], datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    return {
        "objective": objective,
        "theme": ai_data["theme"],
        "marketing_strategy": ai_data["marketing_strategy"],
        "messaging_approach": ai_data["messaging_approach"],
        "cta": ai_data["cta"],
        "outcome": outcome,
        "expected_outcome": ai_data["expected_outcome"],
        "ai_insight": ai_data["ai_insight"],
    }


@app.post("/pitch")
def generate_pitch(req: PitchRequest):
    payload = {"product": req.product.strip(), "target": req.target.strip()}
    fallback = {
        "opening_hook": f"{payload['target']} are under pressure to deliver more revenue with less manual work.",
        "problem_framing": f"Most {payload['target']} lose momentum because reps juggle disconnected workflows and inconsistent follow-up.",
        "product_positioning": f"{payload['product']} brings lead intelligence, outreach, and execution into one workflow so teams move faster.",
        "objection_handling": "Implementation is lightweight, ROI is visible quickly, and adoption is easier than replacing a full sales stack.",
        "closing_statement": "If this could improve pipeline velocity in the next 30 days, would you be open to a short walkthrough?",
    }
    ai_data = ai_or_fallback(
        "sales_pitch",
        payload,
        "Return only JSON with keys: opening_hook, problem_framing, product_positioning, objection_handling, closing_statement.",
        f"Write a sales pitch for product={payload['product']} targeting {payload['target']}.",
        fallback,
    )
    return {
        "opening_hook": ai_data["opening_hook"],
        "problem_framing": ai_data["problem_framing"],
        "product_positioning": ai_data["product_positioning"],
        "objection_handling": ai_data["objection_handling"],
        "closing_statement": ai_data["closing_statement"],
        "problem": ai_data["problem_framing"],
        "value_prop": ai_data["product_positioning"],
        "objection": ai_data["objection_handling"],
        "closing": ai_data["closing_statement"],
        "ai_insight": ai_data["opening_hook"],
    }


@app.post("/leads")
def score_lead(req: ScoreRequest):
    score = score_lead_formula(req.budget, req.interest)
    category = category_for_score(score)
    recommendation = recommendation_for_category(category)

    payload = {
        "company": req.company,
        "budget": req.budget,
        "interest": req.interest,
        "score": score,
        "category": category,
        "industry": req.industry or "Unknown",
        "region": req.region or "Unknown",
    }
    fallback = {
        "explanation": f"This lead is {category.lower()} because the budget and interest signals combine to a score of {score}, indicating {recommendation.lower()}.",
    }
    ai_data = ai_or_fallback(
        "lead_scoring_explanation",
        payload,
        "Return only JSON with key explanation. Explain why the lead score maps to Hot, Warm, or Cold in 1-2 sentences.",
        f"Explain lead quality for company={req.company}, budget={req.budget}, interest={req.interest}, score={score}, category={category}.",
        fallback,
    )

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO leads (
                company, budget, interest, score, category, industry, region,
                contact_name, contact_email, deal_stage, last_contacted, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.company.strip(), req.budget, req.interest, score, category, req.industry, req.region,
                req.contact_name, req.contact_email, req.deal_stage, datetime.utcnow().isoformat(), req.notes,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()

    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,
        "explanation": ai_data["explanation"],
    }


@app.get("/leads")
def get_all_leads():
    with db_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT id, company, budget, interest, score, category, industry, region,
                   contact_name, contact_email, deal_stage, last_contacted, notes, created_at
            FROM leads
            ORDER BY score DESC, created_at DESC
            """
        ).fetchall()
    return {"leads": serialize_rows(rows)}


@app.post("/social")
def generate_social(req: ContentRequest):
    payload = {"product": req.product.strip(), "platform": req.platform.strip()}
    tone_map = {
        "LinkedIn": "professional and insight-driven",
        "Instagram": "visual, energetic, and lifestyle-oriented",
        "X / Twitter": "sharp, concise, and timely",
        "Twitter": "sharp, concise, and timely",
    }
    tone = tone_map.get(payload["platform"], "professional")
    fallback = {
        "caption": f"{payload['product']} helps teams move faster with clearer pipeline decisions and better outreach execution.",
        "hashtags": f"#{payload['product'].replace(' ', '')} #SalesAI #Growth #B2B",
        "tone": tone,
        "ai_insight": f"The message is adapted to {payload['platform']} with a {tone} tone.",
    }
    ai_data = ai_or_fallback(
        "social_generator",
        payload,
        "Return only JSON with keys: caption, hashtags, tone, ai_insight. Hashtags must be a single string.",
        f"Create a {payload['platform']} social post for product={payload['product']}. Tone should match the platform.",
        fallback,
    )
    return ai_data


@app.post("/email")
def generate_email(req: EmailRequest):
    payload = {
        "recipient": req.recipient.strip(),
        "product": req.product.strip(),
        "context": req.context.strip(),
    }
    fallback = {
        "subject": f"Idea to improve {payload['context']}",
        "body": (
            f"Hi {payload['recipient']},\n\n"
            f"I noticed the challenge around {payload['context']}. {payload['product']} helps teams prioritize the right leads, automate follow-up, and keep deals moving.\n\n"
            "Would you be open to a short conversation this week?\n\nBest regards,\nSalesSpark AI"
        ),
        "follow_up_suggestion": "Follow up in 3 days with a short proof point or customer outcome.",
    }
    ai_data = ai_or_fallback(
        "email_outreach",
        payload,
        "Return only JSON with keys: subject, body, follow_up_suggestion.",
        f"Write a personalized outreach email to {payload['recipient']} about {payload['product']} using this context: {payload['context']}.",
        fallback,
    )
    return {
        "subject": ai_data["subject"],
        "body": ai_data["body"],
        "follow_up_suggestion": ai_data["follow_up_suggestion"],
        "follow_up_tip": ai_data["follow_up_suggestion"],
    }

@app.post("/predict/campaign")
def predict_campaign(req: PredictionRequest):
    with db_conn() as conn:
        cur = conn.cursor()
        total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        avg_raw = cur.execute("SELECT AVG(score) FROM leads").fetchone()[0]
        avg_score = round(avg_raw, 1) if avg_raw is not None else 0.0
        hot_leads = cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80").fetchone()[0]
        platform_campaigns = cur.execute("SELECT COUNT(*) FROM campaigns WHERE platform = ?", (req.platform,)).fetchone()[0]
        goal_campaigns = cur.execute("SELECT COUNT(*) FROM campaigns WHERE goal = ?", (req.goal,)).fetchone()[0]

    engagement_score = 40 + (avg_score * 0.6)
    engagement_prob = int(max(0, min(100, round(engagement_score))))
    hot_ratio = (hot_leads / total_leads) if total_leads else 0
    conversion_prob = int(max(5, min(65, round((engagement_prob * 0.18) + (hot_ratio * 20)))))

    if total_leads == 0:
        risk = "High"
        data_source = "Rule-based fallback"
    elif avg_score >= 70 and hot_leads >= 3:
        risk = "Low"
        data_source = "Live Database"
    elif avg_score >= 50:
        risk = "Medium"
        data_source = "Live Database"
    else:
        risk = "High"
        data_source = "Live Database"

    payload = {
        "platform": req.platform,
        "goal": req.goal,
        "average_lead_score": avg_score,
        "total_leads": total_leads,
        "engagement_score": engagement_prob,
    }
    fallback = {
        "reasoning": f"Predicted engagement is {engagement_prob}% using the fixed formula 40 + (average lead score x 0.6). Current average score is {avg_score}/100 across {total_leads} leads.",
        "campaign_improvement_suggestions": "Increase hot lead volume, tighten audience targeting, and reuse top-performing messaging on the selected platform.",
    }
    ai_data = ai_or_fallback(
        "campaign_prediction_explanation",
        payload,
        "Return only JSON with keys: reasoning, campaign_improvement_suggestions.",
        f"Explain a campaign prediction for platform={req.platform}, goal={req.goal}, average lead score={avg_score}, total leads={total_leads}, predicted engagement={engagement_prob}.",
        fallback,
    )

    return {
        "engagement_prob": engagement_prob,
        "predicted_engagement": engagement_prob,
        "conversion_prob": conversion_prob,
        "risk_level": risk,
        "data_source": data_source,
        "metrics_used": {
            "total_leads": total_leads,
            "avg_lead_score": avg_score,
            "platform_campaigns": platform_campaigns,
            "goal_campaigns": goal_campaigns,
            "hot_leads": hot_leads,
        },
        "reasoning": ai_data["reasoning"],
        "suggestions": ai_data["campaign_improvement_suggestions"],
        "explanation": f"{ai_data['reasoning']} Suggested improvements: {ai_data['campaign_improvement_suggestions']}",
    }


@app.post("/market/analyze")
def market_intelligence_analysis(req: MarketAnalysisRequest):
    industry = req.industry.strip() or "saas"
    region = req.region.strip() or "Global"
    horizon = req.time_horizon.strip() or "Mid"

    db_context = get_market_context()
    snapshot = get_pipeline_snapshot()
    baseline = INDUSTRY_BASELINES.get(industry.lower(), INDUSTRY_BASELINES["saas"])
    region_mult = _lookup_ci(REGION_MULTIPLIERS, region, REGION_MULTIPLIERS["Global"])
    time_mult = _lookup_ci(TIME_MULTIPLIERS, horizon, TIME_MULTIPLIERS["Mid"])

    demand_score = int(max(0, min(100, round(baseline["demand"] * region_mult["demand"] * time_mult["demand"]))))
    competition_score = int(max(0, min(100, round(baseline["competition"] * region_mult["competition"]))))
    opportunity_score = int(max(0, min(100, round(baseline["opportunity"] * time_mult["opportunity"]))))
    saturation = int(round((competition_score + (100 - opportunity_score)) / 2))
    search_summary = try_market_search(industry, region)

    payload = {
        "industry": industry,
        "region": region,
        "time_horizon": horizon,
        "industries_in_leads": db_context["industries"],
        "regions_in_leads": db_context["regions"],
        "campaign_products": db_context["products"],
        "search_summary": search_summary,
    }
    fallback = {
        "market_trend_summary": f"{industry.title()} demand in {region} remains healthy, especially where buyers want faster pipeline execution and clearer ROI.",
        "demand_level": f"Demand is {demand_score}/100 with strongest interest around measurable efficiency gains.",
        "competition_overview": f"Competition is {competition_score}/100, so tighter positioning and proof-based messaging are important.",
        "opportunity_insights": f"Opportunity is {opportunity_score}/100. Align messaging with the industries already converting in your pipeline and prioritize the best-fit region.",
        "channels": baseline["channels"],
    }
    ai_data = ai_or_fallback(
        "market_intelligence",
        payload,
        "Return only JSON with keys: market_trend_summary, demand_level, competition_overview, opportunity_insights, channels. channels must be an object with channel names and 0-100 values.",
        (
            f"Analyze market intelligence for industry={industry}, region={region}, horizon={horizon}. "
            f"Internal DB context: industries={db_context['industries']}, regions={db_context['regions']}, campaign products={db_context['products']}. "
            f"Current pipeline snapshot: {snapshot}. External search summary: {search_summary or 'none available'}."
        ),
        fallback,
    )

    channels = normalize_channels(ai_data.get("channels"), baseline["channels"])
    insight = (
        f"Trend: {ai_data['market_trend_summary']} Demand: {ai_data['demand_level']} "
        f"Competition: {ai_data['competition_overview']} Opportunity: {ai_data['opportunity_insights']}"
    )

    return {
        "insight": insight,
        "market_trend_summary": ai_data["market_trend_summary"],
        "demand_level": ai_data["demand_level"],
        "competition_overview": ai_data["competition_overview"],
        "opportunity_insights": ai_data["opportunity_insights"],
        "demand_trend": build_demand_trend(demand_score, horizon, snapshot["avg_score"]),
        "market_matrix": {
            "competition": competition_score,
            "opportunity": opportunity_score,
            "saturation": saturation,
        },
        "channels": channels,
        "meta": {
            "industry": industry,
            "region": region,
            "horizon": horizon,
            "db_context": db_context,
            "external_data_used": bool(search_summary),
        },
    }


@app.get("/dashboard")
def dashboard():
    snapshot = get_pipeline_snapshot()
    with db_conn() as conn:
        cur = conn.cursor()
        best_platform_row = cur.execute(
            "SELECT platform, COUNT(*) AS cnt FROM campaigns GROUP BY platform ORDER BY cnt DESC, platform ASC LIMIT 1"
        ).fetchone()
    metrics = {
        "total_leads": snapshot["total_leads"],
        "hot_leads": snapshot["hot_leads"],
        "warm_leads": snapshot["warm_leads"],
        "cold_leads": snapshot["cold_leads"],
        "avg_lead_score": snapshot["avg_score"],
        "total_campaigns": snapshot["total_campaigns"],
        "best_platform": best_platform_row["platform"] if best_platform_row else "N/A",
        "lead_quality_trend": "Improving" if snapshot["avg_score"] >= 60 else "Stable" if snapshot["avg_score"] >= 45 else "Needs Attention",
    }
    return {"data_source": "Live Database" if snapshot["total_leads"] else "Empty Database", "metrics": metrics}


@app.get("/actions/next")
def next_actions():
    with db_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT id, company, score, interest, category, deal_stage, last_contacted
            FROM leads
            ORDER BY score DESC, interest DESC, created_at DESC
            LIMIT 5
            """
        ).fetchall()
    if not rows:
        return {"actions": [], "message": "No leads available. Generate leads to see prioritized actions."}

    actions = []
    for row in rows:
        if row["score"] >= 85:
            action = f"Contact highest scoring lead at {row['company']} today"
        elif row["category"] == "Warm":
            action = f"Schedule follow-up with {row['company']} and share a case study"
        else:
            action = f"Generate outreach email for {row['company']} and re-engage the account"

        reason = f"{row['company']} is in {row['deal_stage'] or 'Prospecting'} with score {row['score']}/100 and interest {row['interest']}/10."
        priority_score = round(row["score"] * 0.75 + row["interest"] * 2.5, 1)
        actions.append(
            {
                "lead_id": row["id"],
                "company": row["company"],
                "category": row["category"],
                "action": action,
                "reason": reason,
                "score": row["score"],
                "priority_score": priority_score,
                "deal_stage": row["deal_stage"],
            }
        )
    return {"actions": actions}


@app.get("/trends/sales")
def sales_trends():
    with db_conn() as conn:
        cur = conn.cursor()
        total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        if total_leads < 4:
            return {
                "trend": "insufficient",
                "trend_direction": "Insufficient data - add more leads",
                "risk_flags": [],
                "opportunity_flags": [{"alert": "Build your pipeline to unlock trend analysis", "reason": f"Only {total_leads} leads available."}],
                "reason": f"Only {total_leads} leads. Need at least 4 for momentum analysis.",
            }

        window_size = max(2, min(6, total_leads // 2))
        recent_scores = [row[0] for row in cur.execute("SELECT score FROM leads ORDER BY created_at DESC LIMIT ?", (window_size,)).fetchall()]
        older_scores = [row[0] for row in cur.execute("SELECT score FROM leads ORDER BY created_at ASC LIMIT ?", (window_size,)).fetchall()]
        hot_count = cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80").fetchone()[0]
        avg_score = cur.execute("SELECT AVG(score) FROM leads").fetchone()[0] or 0

    recent_avg = sum(recent_scores) / len(recent_scores)
    older_avg = sum(older_scores) / len(older_scores)
    diff = round(recent_avg - older_avg, 1)

    if diff > 8:
        trend = "improving"
        trend_direction = f"Lead quality is up {diff} points"
    elif diff < -8:
        trend = "declining"
        trend_direction = f"Lead quality is down {abs(diff)} points"
    else:
        trend = "stable"
        trend_direction = "Lead quality is holding steady"

    risk_flags = []
    if hot_count == 0:
        risk_flags.append({"alert": "No hot leads in pipeline", "reason": "There are currently no leads above the 80-point threshold."})
    if avg_score < 50:
        risk_flags.append({"alert": "Average lead quality below target", "reason": f"Average score is {avg_score:.1f}/100."})
    if trend == "declining":
        risk_flags.append({"alert": "Sales momentum is slipping", "reason": f"Recent leads are {abs(diff)} points weaker than older leads."})

    opportunity_flags = []
    if hot_count >= 3:
        opportunity_flags.append({"alert": "Hot lead cluster ready for action", "reason": f"{hot_count} leads are in the Hot range."})
    if trend == "improving":
        opportunity_flags.append({"alert": "Momentum is improving", "reason": f"Recent lead quality is up by {diff} points."})

    return {
        "trend": trend,
        "trend_direction": trend_direction,
        "trend_reason": f"Recent average: {recent_avg:.1f}, older average: {older_avg:.1f}, difference: {diff}.",
        "risk_flags": risk_flags,
        "opportunity_flags": opportunity_flags,
        "metrics": {
            "total_leads": total_leads,
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1),
            "hot_leads": hot_count,
            "avg_score": round(avg_score, 1),
        },
    }


@app.get("/alerts")
def get_alerts():
    snapshot = get_pipeline_snapshot()
    alerts = []
    if snapshot["hot_leads"] == 0:
        alerts.append({"level": "warning", "message": "No hot leads in pipeline", "reason": "Create or qualify more high-intent opportunities."})
    if snapshot["avg_score"] < 50:
        alerts.append({"level": "warning", "message": "Average lead quality below target", "reason": f"Average score is {snapshot['avg_score']}/100."})
    if snapshot["total_leads"] < 3:
        alerts.append({"level": "info", "message": "Low recent inbound activity", "reason": "The pipeline is still small, so analytics will be less stable."})
    return {"alerts": alerts}


@app.post("/deal/assist")
def deal_assist(req: DealAssistRequest):
    with db_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, company, budget, interest, score, category, industry, region, deal_stage, notes FROM leads WHERE id = ?",
            (req.lead_id,),
        ).fetchone()
    if not row:
        return {"error": f"Lead ID {req.lead_id} not found"}

    urgency_level = "High" if row["score"] >= 80 else "Medium" if row["score"] >= 55 else "Low"
    fallback = {
        "closing_strategy": f"Use a personalized {row['deal_stage'] or 'consultative'} close focused on {row['company']}'s business priorities.",
        "negotiation_advice": f"Anchor on ROI, tie pricing to the available budget of ${row['budget']:,}, and address implementation risk early.",
        "recommended_next_step": "Book a decision-maker call and send a concise recap with ROI proof points.",
    }
    ai_data = ai_or_fallback(
        "deal_assist",
        {"lead_id": req.lead_id, "score": row["score"], "company": row["company"], "budget": row["budget"], "industry": row["industry"], "deal_stage": row["deal_stage"]},
        "Return only JSON with keys: closing_strategy, negotiation_advice, recommended_next_step.",
        f"Create a personalized closing plan for company={row['company']}, score={row['score']}, budget={row['budget']}, industry={row['industry']}, deal_stage={row['deal_stage']}, notes={row['notes']}.",
        fallback,
    )
    result = {
        "closing_strategy": ai_data["closing_strategy"],
        "discount_range": "0-5%" if row["score"] >= 80 else "5-10%" if row["score"] >= 60 else "10-15%",
        "objection_focus": ai_data["negotiation_advice"],
        "negotiation_advice": ai_data["negotiation_advice"],
        "recommended_next_step": ai_data["recommended_next_step"],
        "urgency_level": urgency_level,
        "explanation": f"{ai_data['recommended_next_step']} Lead profile: {row['category']} lead in {row['deal_stage'] or 'Prospecting'} with score {row['score']}/100.",
    }
    log_interaction(req.lead_id, "deal_assist", result)
    return result


@app.post("/followup/plan")
def followup_plan(req: FollowupRequest):
    with db_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, company, score, category, deal_stage, industry FROM leads WHERE id = ?",
            (req.lead_id,),
        ).fetchone()
    if not row:
        return {"error": f"Lead ID {req.lead_id} not found"}

    fallback = {
        "plan": {
            "day 1": f"Send a personalized outreach email to {row['company']} tied to their {row['industry'] or 'current'} priorities.",
            "day 3": "Share a short demo invitation or customer proof point.",
            "day 7": "Follow up with an ROI-focused message and a clear next step.",
        },
        "note": f"Sequence tailored for a {row['category']} lead in the {row['deal_stage'] or 'Prospecting'} stage.",
    }
    ai_data = ai_or_fallback(
        "followup_plan",
        {"lead_id": req.lead_id, "company": row["company"], "score": row["score"], "deal_stage": row["deal_stage"], "category": row["category"]},
        "Return only JSON with keys: plan and note. plan must be an object with keys 'day 1', 'day 3', and 'day 7'.",
        f"Create a follow-up sequence for company={row['company']}, score={row['score']}, category={row['category']}, deal_stage={row['deal_stage']}, industry={row['industry']}.",
        fallback,
    )
    result = {
        "category": row["category"],
        "score": row["score"],
        "plan": ai_data["plan"],
        "note": ai_data["note"],
    }
    log_interaction(req.lead_id, "followup_plan", result)
    return result

NAVIGATION_URLS = {
    "home": "index.html",
    "sales_copilot": "sales_copilot.html",
    "leads": "leads.html",
    "tools": "tools.html",
    "prediction": "prediction.html",
    "market": "market_intelligence.html",
}


def _normalize_page(page: str) -> str:
    page = (page or "").strip().lower()
    if page == "copilot":
        return "sales_copilot"
    if page == "dashboard":
        return "sales_copilot"
    if page in {"campaigns", "campaign"}:
        return "tools"
    if page in {"home", "landing", "index", "index.html"}:
        return "home"
    return page


def _pipeline_brief(db_context: Dict[str, Any]) -> str:
    return (
        f"Pipeline: {db_context['total_leads']} total leads, {db_context['hot_leads']} hot, "
        f"{db_context['warm_leads']} warm, {db_context['cold_leads']} cold, "
        f"average score {db_context['avg_score']}/100."
    )


def _page_suggestions(current_page: str, db_context: Dict[str, Any]) -> List[str]:
    page = _normalize_page(current_page)
    if page == "leads":
        return [
            f"You have {db_context['hot_leads']} hot leads. Want me to draft follow-up emails?",
            "Ask: Which lead should I focus on?",
            "Ask: Generate a closing strategy for the top lead.",
        ]
    if page == "tools":
        return [
            "Want me to create a campaign strategy for your product?",
            "Ask: Write a cold email for SaaS founders.",
            "Ask: Generate a sales pitch for my product.",
        ]
    if page == "prediction":
        return [
            "Ask: Explain the prediction in simple terms.",
            "Ask: How can I improve campaign performance?",
            "Ask: Show me risks in my current pipeline.",
        ]
    if page == "market":
        return [
            "Ask: Summarize market opportunities for my pipeline.",
            "Ask: Which region should I prioritize next?",
            "Ask: Compare demand and competition quickly.",
        ]
    return [
        "Ask: Show my leads.",
        "Ask: Help me close more deals.",
        "Ask: Create a campaign for a SaaS product targeting startups.",
    ]


def _resolve_lead(identifier: Any) -> Optional[sqlite3.Row]:
    """Find a lead by id or company name. The agent speaks in names, the DB in ids."""
    if identifier is None or identifier == "":
        return None
    with db_conn() as conn:
        cur = conn.cursor()
        text = str(identifier).strip()
        if text.isdigit():
            row = cur.execute("SELECT * FROM leads WHERE id = ?", (int(text),)).fetchone()
            if row:
                return row
        row = cur.execute(
            "SELECT * FROM leads WHERE company = ? COLLATE NOCASE", (text,)
        ).fetchone()
        if row:
            return row
        return cur.execute(
            "SELECT * FROM leads WHERE company LIKE ? COLLATE NOCASE ORDER BY score DESC LIMIT 1",
            (f"%{text}%",),
        ).fetchone()


def _lead_not_found(identifier: Any) -> Dict[str, Any]:
    with db_conn() as conn:
        names = [
            r["company"]
            for r in conn.cursor().execute(
                "SELECT company FROM leads ORDER BY score DESC LIMIT 5"
            ).fetchall()
        ]
    known = ", ".join(names) if names else "none yet"
    return {
        "for_model": (
            f"No lead matches '{identifier}'. Ask the user which lead they mean. "
            f"Leads in the pipeline include: {known}."
        ),
        "event": None,
    }


def execute_chat_tool(name: str, args: Dict[str, Any], current_page: str, db_context: Dict[str, Any]) -> Dict[str, Any]:
    """Run a tool the AI agent requested. Returns {"for_model": str, "event": dict|None}.

    ``for_model`` is fed back to the model so it can narrate the result; ``event``
    (when present) is streamed to the browser to render a rich card or navigate.
    """
    if name == "navigate_to_page":
        page = _normalize_page(args.get("page", ""))
        url = NAVIGATION_URLS.get(page)
        if not url:
            return {"for_model": "That page isn't available in the app.", "event": None}
        label = page.replace("_", " ").title()
        return {
            "for_model": f"Opened the {label} page for the user.",
            "event": {
                "type": "action", "action": "navigate", "page": page, "url": url,
                "response": f"Opening {label}…",
            },
        }

    if name == "analyze_pipeline":
        # Re-read the pipeline instead of using db_context, which was captured before
        # the turn began. score_lead can run earlier in the same turn, and answering
        # from the stale snapshot would omit the lead we just told the user we added.
        live = get_pipeline_snapshot()
        brief = _pipeline_brief(live)
        top = live.get("top_leads") or []
        if top:
            t = top[0]
            brief += f" Top lead: {t['company']} ({t['score']}/100, {t['category']})."
        brief += f" Pipeline health: {live.get('pipeline_health', 'Unknown')}."
        return {"for_model": brief, "event": None}

    if name == "get_next_actions":
        data = next_actions()
        actions = data.get("actions", [])
        if not actions:
            return {"for_model": data.get("message", "No leads yet, so there are no prioritized actions."), "event": None}
        summary = "; ".join(f"{a['company']}: {a['action']}" for a in actions[:5])
        return {
            "for_model": f"Prioritized next actions -> {summary}",
            "event": {"type": "tool_result", "tool": "next_actions", "result": data},
        }

    if name == "generate_campaign":
        result = generate_campaign(CampaignRequest(
            product=(args.get("product") or "your product"),
            audience=(args.get("audience") or "your target buyers"),
            platform=(args.get("platform") or "LinkedIn"),
            goal=(args.get("goal") or "Leads"),
        ))
        return {
            "for_model": f"Campaign ready. Theme: {result['theme']}. Strategy: {result['marketing_strategy']}. CTA: {result['cta']}.",
            "event": {"type": "tool_result", "tool": "generate_campaign", "result": result},
        }

    if name == "draft_email":
        result = generate_email(EmailRequest(
            recipient=(args.get("recipient") or "there"),
            product=(args.get("product") or "SalesSparkAI"),
            context=(args.get("context") or "improving pipeline conversion"),
        ))
        return {
            "for_model": f"Email drafted. Subject: {result['subject']}.",
            "event": {"type": "tool_result", "tool": "generate_email", "result": result},
        }

    if name == "generate_pitch":
        result = generate_pitch(PitchRequest(
            product=(args.get("product") or "SalesSparkAI"),
            target=(args.get("target") or "sales teams"),
        ))
        return {
            "for_model": f"Pitch ready. Opening hook: {result['opening_hook']}.",
            "event": {"type": "tool_result", "tool": "generate_pitch", "result": result},
        }

    if name == "get_market_intelligence":
        result = market_intelligence_analysis(MarketAnalysisRequest(
            industry=(args.get("industry") or "saas"),
            region=(args.get("region") or "Global"),
            time_horizon=(args.get("time_horizon") or "Mid"),
        ))
        return {
            "for_model": (
                f"Market read -> {result['demand_level']} {result['market_trend_summary']} "
                f"Opportunity: {result['opportunity_insights']}"
            ),
            "event": {"type": "tool_result", "tool": "analyze_market", "result": result},
        }

    if name == "list_leads":
        category = (args.get("category") or "").strip().title()
        limit = min(int(args.get("limit") or 5), 10)
        sql = "SELECT id, company, score, category, deal_stage, industry FROM leads"
        params: tuple = ()
        if category in ("Hot", "Warm", "Cold"):
            sql += " WHERE category = ?"
            params = (category,)
        sql += " ORDER BY score DESC LIMIT ?"
        with db_conn() as conn:
            rows = conn.cursor().execute(sql, params + (limit,)).fetchall()
        if not rows:
            return {"for_model": f"No {category or ''} leads found.".strip(), "event": None}
        leads = [dict(r) for r in rows]
        listing = "; ".join(
            f"{r['company']} ({r['score']}/100, {r['category']}, {r['deal_stage'] or 'Prospecting'})"
            for r in leads
        )
        return {
            "for_model": f"Leads -> {listing}",
            "event": {"type": "tool_result", "tool": "list_leads", "result": {"leads": leads}},
        }

    if name == "score_lead":
        company = (args.get("company") or "").strip()
        # Scoring WRITES a lead row, so a missing budget or interest must stop the
        # tool, not get defaulted. Coercing them to 0/5 passes ScoreRequest's own
        # bounds, which would silently persist a lead the user never described.
        missing = [
            label for label, value in (
                ("a company name", company),
                ("a budget in dollars", args.get("budget")),
                ("an interest level from 1-10", args.get("interest")),
            ) if value in (None, "")
        ]
        if missing:
            return {
                "for_model": (
                    "Do NOT score this lead yet — you are missing " + ", ".join(missing) +
                    ". Ask the user for the missing values and call score_lead again once "
                    "they answer. Do not guess or assume them."
                ),
                "event": None,
            }
        try:
            result = score_lead(ScoreRequest(
                company=company,
                budget=int(args["budget"]),
                interest=int(args["interest"]),
                industry=args.get("industry"),
                region=args.get("region"),
            ))
        except (ValidationError, ValueError, TypeError):
            return {
                "for_model": (
                    "Scoring needs a company name, a budget in dollars, and an interest level "
                    "from 1-10. Ask the user for whatever is missing or invalid."
                ),
                "event": None,
            }
        result["company"] = company
        return {
            "for_model": f"Scored {company}: {result['score']}/100 ({result['category']}). {result['recommendation']}",
            "event": {"type": "tool_result", "tool": "score_lead", "result": result},
        }

    if name == "get_deal_strategy":
        row = _resolve_lead(args.get("company"))
        if not row:
            return _lead_not_found(args.get("company"))
        result = deal_assist(DealAssistRequest(lead_id=row["id"]))
        result["company"] = row["company"]
        return {
            "for_model": (
                f"Closing plan for {row['company']} ({result['urgency_level']} urgency): "
                f"{result['closing_strategy']} Next step: {result['recommended_next_step']}"
            ),
            "event": {"type": "tool_result", "tool": "deal_strategy", "result": result},
        }

    if name == "get_followup_plan":
        row = _resolve_lead(args.get("company"))
        if not row:
            return _lead_not_found(args.get("company"))
        result = followup_plan(FollowupRequest(lead_id=row["id"]))
        result["company"] = row["company"]
        steps = "; ".join(f"{k}: {v}" for k, v in (result.get("plan") or {}).items())
        return {
            "for_model": f"Follow-up plan for {row['company']} -> {steps}",
            "event": {"type": "tool_result", "tool": "followup_plan", "result": result},
        }

    if name == "predict_campaign":
        result = predict_campaign(PredictionRequest(
            platform=(args.get("platform") or "LinkedIn"),
            goal=(args.get("goal") or "Leads"),
        ))
        return {
            "for_model": (
                f"Prediction -> engagement {result['engagement_prob']}%, conversion "
                f"{result['conversion_prob']}%, risk {result['risk_level']}. {result['reasoning']}"
            ),
            "event": {"type": "tool_result", "tool": "predict_campaign", "result": result},
        }

    if name == "generate_social":
        result = generate_social(ContentRequest(
            product=(args.get("product") or "SalesSparkAI"),
            platform=(args.get("platform") or "LinkedIn"),
        ))
        return {
            "for_model": f"Social post drafted for {args.get('platform') or 'LinkedIn'}.",
            "event": {"type": "tool_result", "tool": "generate_social", "result": result},
        }

    return {"for_model": f"Unknown tool '{name}'.", "event": None}


# The model occasionally answers a data question by navigating (e.g. "how is my
# pipeline?" -> opens Leads). Navigation is disruptive and hard to undo, so we
# only honour it when the user actually asked to be taken somewhere.
NAV_REQUEST_RE = re.compile(
    r"\b(open|show|go\s*to|goto|take\s*me|navigate|bring\s*up|switch\s*to|view|see|visit|"
    r"back\s*to|jump\s*to|launch)\b",
    re.IGNORECASE,
)


def _wants_navigation(message: str) -> bool:
    return bool(NAV_REQUEST_RE.search(message or ""))


def _chat_executor(message: str, current_page: str, db_context: Dict[str, Any]) -> Callable[[str, dict], dict]:
    def _run(name: str, args: dict) -> dict:
        if name == "navigate_to_page" and not _wants_navigation(message):
            return {
                "for_model": (
                    "Do NOT navigate — the user asked a question, they did not ask to open a page. "
                    "Answer them in the chat instead, using analyze_pipeline if you need their data."
                ),
                "event": None,
            }
        return execute_chat_tool(name, args, current_page, db_context)
    return _run


# ── Deterministic fallback ──────────────────────────────────────────────────────
# The LLM is not the only way to answer. When Groq is unconfigured or out of quota,
# route the message through plain intent matching and run the same tools directly,
# so pipeline questions and generation still work instead of the copilot going dead.
# (The generators degrade to templates without Groq, so they work here too.)
_OFFLINE_INTENTS: List[tuple] = [
    # Scoring writes a row and needs numbers we cannot reliably parse from prose, so
    # it is never run here — it asks instead. This must precede list_leads, or "add
    # Acme as a new lead" would match on the word "lead" and just list the book.
    (re.compile(r"\b(add|create|score|rate|evaluate)\b.{0,30}\b(lead|prospect|company)\b|\bscore\s+\w+", re.I),
     "__ask_score"),
    (re.compile(r"\b(next\s+(best\s+)?(action|step)s?|what\s+should\s+i\s+do|who\s+(do\s+i|should\s+i)\s+(call|contact))\b", re.I),
     "get_next_actions"),
    (re.compile(r"\b(pipeline|how\s+many\s+leads|health|overview|summary|how\s+am\s+i\s+doing)\b", re.I),
     "analyze_pipeline"),
    (re.compile(r"\b(follow[\s-]?up|sequence|cadence)\b", re.I), "get_followup_plan"),
    (re.compile(r"\b(close|closing|deal\s+strategy|negotiat)\w*\b", re.I), "get_deal_strategy"),
    (re.compile(r"\b(campaign)\b", re.I), "generate_campaign"),
    (re.compile(r"\b(cold\s+)?(email|outreach)\b", re.I), "draft_email"),
    (re.compile(r"\b(pitch)\b", re.I), "generate_pitch"),
    (re.compile(r"\b(social|linkedin\s+post|tweet|post)\b", re.I), "generate_social"),
    (re.compile(r"\b(market|demand|competit\w+|industry\s+outlook)\b", re.I), "get_market_intelligence"),
    (re.compile(r"\b(leads?|hot|warm|cold|prospects?)\b", re.I), "list_leads"),
]

_OFFLINE_NOTE = (
    "The AI model is unavailable right now (no API key, or today's quota is spent), "
    "so I answered from your data directly."
)


def _offline_args(tool: str, message: str) -> Dict[str, Any]:
    """Best-effort arguments for a tool chosen by regex rather than by the model."""
    args: Dict[str, Any] = {}
    if tool == "list_leads":
        for cat in ("hot", "warm", "cold"):
            if re.search(rf"\b{cat}\b", message, re.I):
                args["category"] = cat.title()
                break
    elif tool in ("get_deal_strategy", "get_followup_plan"):
        # Match the message against known company names — the agent normally does this.
        # Longest name first, so "Meta Platforms" wins over "Meta".
        with db_conn() as conn:
            rows = conn.cursor().execute("SELECT company FROM leads").fetchall()
        names = sorted(
            {(r["company"] or "").strip() for r in rows if (r["company"] or "").strip()},
            key=len, reverse=True,
        )
        for company in names:
            if company.lower() in message.lower():
                args["company"] = company
                break
    elif tool == "get_market_intelligence":
        m = re.search(r"\b(?:for|in|about)\s+([A-Za-z][\w\s&-]{2,30})", message)
        if m:
            args["industry"] = m.group(1).strip()
    return args


def _offline_text(tool: str, out: Dict[str, Any]) -> str:
    """A human sentence for the chat bubble. `for_model` is phrased for the LLM."""
    result = (out.get("event") or {}).get("result") or {}
    if tool == "analyze_pipeline":
        return out.get("for_model", "")          # already a plain sentence
    if tool == "list_leads":
        leads = result.get("leads") or []
        return f"Here are your top {len(leads)} lead{'' if len(leads) == 1 else 's'}."
    if tool == "get_next_actions":
        actions = result.get("actions") or []
        return f"{len(actions)} lead{'' if len(actions) == 1 else 's'} need attention — here they are, highest score first."
    if tool == "get_deal_strategy":
        return f"Here's a closing plan for {result.get('company', 'that lead')}."
    if tool == "get_followup_plan":
        return f"Here's a follow-up sequence for {result.get('company', 'that lead')}."
    if tool == "generate_campaign":
        return "Here's a campaign you can run."
    if tool == "draft_email":
        return "Here's an outreach email you can send."
    if tool == "generate_pitch":
        return "Here's a pitch you can use."
    if tool == "generate_social":
        return "Here's a social post."
    if tool == "get_market_intelligence":
        return "Here's the market read."
    return out.get("for_model", "")


def offline_agent(message: str, current_page: str, db_context: Dict[str, Any]) -> Iterator[dict]:
    """Answer without the LLM, emitting the same event shapes as ``stream_agent``."""
    page = _normalize_page(message.replace(" ", "_")) if _wants_navigation(message) else ""
    if page in NAVIGATION_URLS:
        out = execute_chat_tool("navigate_to_page", {"page": page}, current_page, db_context)
        if out.get("event"):
            yield out["event"]
            return

    for pattern, tool in _OFFLINE_INTENTS:
        if not pattern.search(message):
            continue
        if tool == "__ask_score":
            yield {"type": "token", "text": (
                "To score a lead I need three things: the company name, the budget in "
                "dollars, and their interest level from 1 to 10.\n\n"
                "Send them like: `Score Acme, budget 50000, interest 8`.\n\n"
                f"_{_OFFLINE_NOTE}_"
            )}
            return
        args = _offline_args(tool, message)
        if tool in ("get_deal_strategy", "get_followup_plan") and "company" not in args:
            continue     # no known company named — this isn't really that intent
        yield {"type": "tool", "phase": "start", "name": tool,
               "label": TOOL_LABELS.get(tool, "Working")}
        out = execute_chat_tool(tool, args, current_page, db_context)
        if out.get("event"):
            yield out["event"]
        yield {"type": "token", "text": f"{_offline_text(tool, out)}\n\n_{_OFFLINE_NOTE}_"}
        return

    yield {"type": "token", "text": (
        "⚠️ The AI model is unavailable right now — no API key is set, or today's quota is spent.\n\n"
        "I can still answer from your data. Try:\n"
        "- How is my pipeline?\n"
        "- Which leads are hot?\n"
        "- What should I do next?\n"
        "- Draft a campaign / email / pitch"
    )}


def _sse(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.post("/chat")
def chat_assistant(req: ChatRequest):
    """Non-streaming chat: runs the tool-calling agent and returns a final dict.

    Kept as a graceful fallback for clients that cannot consume the SSE stream.
    """
    user_message = (req.message or "").strip()
    if not user_message:
        return {"error": "Message must not be empty."}

    db_context = get_pipeline_snapshot()
    current_page = req.current_page or "unknown"
    suggestions = _page_suggestions(current_page, db_context)

    try:
        pipeline_summary = build_pipeline_summary(db_context)
        messages = build_messages(user_message, pipeline_summary, current_page, req.history or [])
        result = run_agent(messages, _chat_executor(user_message, current_page, db_context))
    except Exception as exc:
        logger.error("[CHAT] %s: %s", type(exc).__name__, exc)
        result = {"unavailable": "error"}

    # The model never answered — fall back to the deterministic path.
    if result.get("unavailable"):
        result = _drain_offline(user_message, current_page, db_context)

    result.setdefault("suggestions", suggestions)
    return result


def _drain_offline(message: str, current_page: str, db_context: Dict[str, Any]) -> Dict[str, Any]:
    """Collect ``offline_agent`` events into the same dict shape ``run_agent`` returns."""
    text_parts: List[str] = []
    tools: List[Dict[str, Any]] = []
    out: Dict[str, Any] = {}
    for ev in offline_agent(message, current_page, db_context):
        if ev.get("type") == "token":
            text_parts.append(ev.get("text", ""))
        elif ev.get("type") == "tool_result":
            tools.append({"tool": ev.get("tool"), "result": ev.get("result")})
        elif ev.get("type") == "action":
            out["action"] = "navigate"
            out["page"] = ev.get("page")
            out["url"] = ev.get("url")
            text_parts.append(ev.get("response", ""))
    out["response"] = "".join(text_parts).strip() or "Done."
    if tools:
        out["tools"] = tools
    return out


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Streaming chat over Server-Sent Events.

    Emits newline-delimited ``data: {json}`` events of type:
      token | tool | tool_result | action | suggestions | done
    """
    user_message = (req.message or "").strip()
    db_context = get_pipeline_snapshot()
    current_page = req.current_page or "unknown"
    suggestions = _page_suggestions(current_page, db_context)
    history = req.history or []

    def event_stream():
        if not user_message:
            yield _sse({"type": "token", "text": "Please type a message."})
            yield _sse({"type": "done"})
            return
        try:
            pipeline_summary = build_pipeline_summary(db_context)
            messages = build_messages(user_message, pipeline_summary, current_page, history)
            for ev in stream_agent(messages, _chat_executor(user_message, current_page, db_context)):
                # The model never answered (no key, or out of quota). stream_agent only
                # sends this before anything has streamed or run, so replaying the turn
                # deterministically cannot double-execute a tool.
                if ev.get("type") == "unavailable":
                    for off in offline_agent(user_message, current_page, db_context):
                        yield _sse(off)
                    break
                yield _sse(ev)
        except Exception as exc:
            logger.error("[CHAT_STREAM] %s: %s", type(exc).__name__, exc)
            yield _sse({"type": "token", "text": "Sorry, I hit an error. Please try again."})
        yield _sse({"type": "suggestions", "items": suggestions})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {
        "status": "SalesSpark AI Backend Running",
        "version": "4.0",
        "ai_ready": groq_ready(),
    }


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(os.path.join(PROJECT_ROOT, "index.html"))


@app.get("/{page_name}", include_in_schema=False)
def serve_page(page_name: str):
    allowed_pages = {
        "index.html",
        "tools.html",
        "prediction.html",
        "market_intelligence.html",
        "sales_copilot.html",
        "leads.html",
        "favicon.ico",
    }
    if page_name not in allowed_pages:
        raise HTTPException(status_code=404, detail="File not found")

    if page_name == "favicon.ico":
        return FileResponse(os.path.join(PROJECT_ROOT, "assets", "favicon.png"))

    return FileResponse(os.path.join(PROJECT_ROOT, page_name))

@app.get("/copilot/insights")
def copilot_insights():
    snapshot = get_pipeline_snapshot()
    distribution = {
        "hot": snapshot["hot_leads"],
        "warm": snapshot["warm_leads"],
        "cold": snapshot["cold_leads"],
    }
    fallback = {
        "summary": f"Your pipeline contains {snapshot['hot_leads']} hot leads, {snapshot['warm_leads']} warm leads, and {snapshot['cold_leads']} cold leads with an average score of {snapshot['avg_score']}/100.",
        "insights": [
            f"Your pipeline currently contains {snapshot['hot_leads']} hot leads with strong purchasing potential.",
            "Prioritize the highest scoring account first and keep warm leads moving with fast follow-up.",
            "Use outreach and campaign tools to improve conversion across the middle of the funnel.",
        ],
    }
    ai_data = ai_or_fallback(
        "copilot_insights",
        {"snapshot": snapshot, "distribution": distribution},
        "Return only JSON with keys: summary and insights. insights must be an array of exactly 3 concise strings.",
        f"Generate sales copilot insights for total leads={snapshot['total_leads']}, average score={snapshot['avg_score']}, distribution={distribution}.",
        fallback,
    )
    return ai_data














