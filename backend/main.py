from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
from typing import Any, Dict, List, Optional
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
    from backend.ai_service import generate_chat_response
except ImportError:
    from ai_service import generate_chat_response

try:
    from backend.phase2_ai import generate_json
except ImportError:
    from phase2_ai import generate_json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "backend", "sales.db")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    company: str
    budget: int
    interest: int = Field(ge=1, le=10)
    industry: Optional[str] = None
    region: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    deal_stage: Optional[str] = "Prospecting"
    notes: Optional[str] = None


class AnalysisRequest(BaseModel):
    industry: str
    product: Optional[str] = ""


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


init_db()


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
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT output FROM ai_outputs WHERE feature = ? AND input_hash = ?",
        (feature, make_hash(payload)),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["output"])
    except json.JSONDecodeError:
        return None


def save_cached_output(feature: str, payload: Dict[str, Any], data: Dict[str, Any]) -> None:
    conn = get_db()
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
    conn.close()


def ai_or_fallback(feature: str, payload: Dict[str, Any], system_prompt: str, user_prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    cached = get_cached_output(feature, payload)
    if cached:
        return cached
    result = generate_json(
        feature=feature,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        fallback=fallback,
    )
    save_cached_output(feature, payload, result)
    return result


def get_pipeline_snapshot() -> Dict[str, Any]:
    conn = get_db()
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
    conn.close()

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
    conn = get_db()
    cur = conn.cursor()
    industries = [row[0] for row in cur.execute("SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND TRIM(industry) != '' ORDER BY industry").fetchall()]
    regions = [row[0] for row in cur.execute("SELECT DISTINCT region FROM leads WHERE region IS NOT NULL AND TRIM(region) != '' ORDER BY region").fetchall()]
    products = [row[0] for row in cur.execute("SELECT DISTINCT product FROM campaigns WHERE product IS NOT NULL AND TRIM(product) != '' ORDER BY product").fetchall()]
    conn.close()
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
    random.seed(seed)
    values = []
    start = max(30, demand_score - 10)
    growth = 3 if horizon == "Short" else 5 if horizon == "Mid" else 7
    for idx in range(6):
        noise = random.randint(-4, 4)
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

    conn = get_db()
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
    conn.close()

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

    conn = get_db()
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
    conn.close()

    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,
        "explanation": ai_data["explanation"],
    }


@app.get("/leads")
def get_all_leads():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, company, budget, interest, score, category, industry, region,
               contact_name, contact_email, deal_stage, last_contacted, notes, created_at
        FROM leads
        ORDER BY score DESC, created_at DESC
        """
    ).fetchall()
    conn.close()
    return {"leads": serialize_rows(rows)}


@app.post("/market")
def market_analysis_tool(req: AnalysisRequest):
    industry = req.industry.strip() or "Technology"
    product = (req.product or "your solution").strip() or "your solution"
    baseline = INDUSTRY_BASELINES.get(industry.lower(), INDUSTRY_BASELINES["technology"])
    fallback = {
        "demand_insight": f"Demand remains solid for {industry} buyers seeking tools that reduce manual work and improve visibility.",
        "competition_overview": f"Competition in {industry} is active, so differentiation should emphasize measurable outcomes over generic features.",
        "opportunity_summary": f"{product} can win by focusing on faster execution, clear ROI, and targeted messaging for operational teams.",
    }
    ai_data = ai_or_fallback(
        "market_tool",
        {"industry": industry, "product": product},
        "Return only JSON with keys: demand_insight, competition_overview, opportunity_summary.",
        f"Analyze market demand, competition, and opportunity for industry={industry}, product={product}.",
        fallback,
    )
    return {
        "trend": ai_data["demand_insight"],
        "demand": f"Demand Index {baseline['demand']}/100",
        "competition": ai_data["competition_overview"],
        "opportunity": ai_data["opportunity_summary"],
        "demand_insight": ai_data["demand_insight"],
        "competition_overview": ai_data["competition_overview"],
        "opportunity_summary": ai_data["opportunity_summary"],
        "ai_insight": ai_data["opportunity_summary"],
    }


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
    conn = get_db()
    cur = conn.cursor()
    total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    avg_raw = cur.execute("SELECT AVG(score) FROM leads").fetchone()[0]
    avg_score = round(avg_raw, 1) if avg_raw is not None else 0.0
    hot_leads = cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80").fetchone()[0]
    platform_campaigns = cur.execute("SELECT COUNT(*) FROM campaigns WHERE platform = ?", (req.platform,)).fetchone()[0]
    goal_campaigns = cur.execute("SELECT COUNT(*) FROM campaigns WHERE goal = ?", (req.goal,)).fetchone()[0]
    conn.close()

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
    region_mult = REGION_MULTIPLIERS.get(region, REGION_MULTIPLIERS["Global"])
    time_mult = TIME_MULTIPLIERS.get(horizon, TIME_MULTIPLIERS["Mid"])

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
    conn = get_db()
    cur = conn.cursor()
    best_platform_row = cur.execute(
        "SELECT platform, COUNT(*) AS cnt FROM campaigns GROUP BY platform ORDER BY cnt DESC, platform ASC LIMIT 1"
    ).fetchone()
    conn.close()
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


@app.get("/recommendations")
def recommendations():
    snapshot = get_pipeline_snapshot()
    if snapshot["avg_score"] < 50:
        action = "Focus on lead quality improvement"
        tip = "Average score is below target. Tighten qualification and use outreach focused on buyer pain points."
    elif snapshot["hot_leads"] < 3:
        action = "Increase hot lead pipeline"
        tip = "There are too few hot leads. Prioritize high-intent accounts and launch a more targeted campaign."
    else:
        action = "Accelerate high-intent conversion"
        tip = "The pipeline has enough hot leads to justify immediate outreach, demos, and tailored closing sequences."
    return {"action": action, "tip": tip, "platform": "LinkedIn"}


@app.get("/segments")
def segments():
    conn = get_db()
    cur = conn.cursor()
    result = {
        "high_value": cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80").fetchone()[0],
        "high_intent": cur.execute("SELECT COUNT(*) FROM leads WHERE interest >= 8").fetchone()[0],
        "price_sensitive": cur.execute("SELECT COUNT(*) FROM leads WHERE budget < 20000").fetchone()[0],
        "low_intent": cur.execute("SELECT COUNT(*) FROM leads WHERE score < 40").fetchone()[0],
    }
    conn.close()
    return result


@app.get("/weekly-report")
def weekly_report():
    snapshot = get_pipeline_snapshot()
    summary = (
        f"This week: {snapshot['total_leads']} total leads, {snapshot['hot_leads']} hot leads, and an average score of {snapshot['avg_score']}/100. "
    )
    if snapshot["hot_leads"] >= 3:
        summary += "Prioritize immediate outreach to your strongest opportunities."
    elif snapshot["avg_score"] < 50:
        summary += "Lead quality is below target, so improve targeting before scaling spend."
    else:
        summary += "Keep nurturing warm leads while building more high-intent demand."
    return {"summary": summary, "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}

@app.get("/actions/next")
def next_actions():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, company, score, interest, category, deal_stage, last_contacted
        FROM leads
        ORDER BY score DESC, interest DESC, created_at DESC
        LIMIT 5
        """
    ).fetchall()
    conn.close()
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
    conn = get_db()
    cur = conn.cursor()
    total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    if total_leads < 4:
        conn.close()
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
    conn.close()

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
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, company, budget, interest, score, category, industry, region, deal_stage, notes FROM leads WHERE id = ?",
        (req.lead_id,),
    ).fetchone()
    conn.close()
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
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, company, score, category, deal_stage, industry FROM leads WHERE id = ?",
        (req.lead_id,),
    ).fetchone()
    conn.close()
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

NAVIGATION_PATTERNS = [
    (re.compile(r"\b(open|show|go\s*to|take\s*me\s*to|back\s*to)\s+(home|landing|landing\s+page|index)\b", re.IGNORECASE), "home"),
    (re.compile(r"\b(open|show|go to|take me to)\s+(sales\s+)?copilot\b", re.IGNORECASE), "sales_copilot"),
    (re.compile(r"\b(open|show|go to|take me to)\s+(my\s+)?leads?\b", re.IGNORECASE), "leads"),
    (re.compile(r"\b(open|show|go to|take me to)\s+(tools?|campaign generator)\b", re.IGNORECASE), "tools"),
    (re.compile(r"\b(open|show|go to|take me to)\s+(prediction|prediction page|campaign prediction)\b", re.IGNORECASE), "prediction"),
    (re.compile(r"\b(open|show|go to|take me to)\s+(market|market insights|market intelligence)\b", re.IGNORECASE), "market"),
]

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


def _detect_navigation_intent(message: str) -> Optional[str]:
    for pattern, page_key in NAVIGATION_PATTERNS:
        if pattern.search(message):
            return page_key
    return None


def _safe_product_from_message(message: str, default_value: str = "your product") -> str:
    match = re.search(r"for\s+([a-z0-9 .&-]+?)(?:\s+targeting|\s+on|\s+using|$)", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default_value


def _safe_audience_from_message(message: str, default_value: str = "startup buyers") -> str:
    match = re.search(r"targeting\s+([a-z0-9 .&-]+?)(?:\s+on|\s+with|$)", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return default_value


def _tool_execution_from_message(message: str, current_page: str, db_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    clean = message.strip()
    low = clean.lower()

    if re.search(r"\b(create|generate|build)\b.*\bcampaign\b", low):
        product = _safe_product_from_message(clean, "SaaS product")
        audience = _safe_audience_from_message(clean, "startup teams")
        req = CampaignRequest(product=product, audience=audience, platform="LinkedIn", goal="Leads")
        result = generate_campaign(req)
        return {
            "response": (
                f"Campaign created for {product}. Theme: {result['theme']}. "
                f"CTA: {result['cta']}. Expected outcome: {result['outcome']}"
            ),
            "action": "tool_result",
            "tool": "generate_campaign",
            "result": result,
            "suggestions": _page_suggestions(current_page, db_context),
        }

    if re.search(r"\b(write|generate|draft)\b.*\b(email|cold email|outreach)\b", low):
        product = _safe_product_from_message(clean, "SalesSparkAI")
        target = _safe_audience_from_message(clean, "SaaS founders")
        req = EmailRequest(recipient=target.title(), product=product, context=f"improving pipeline conversion for {target}")
        result = generate_email(req)
        return {
            "response": f"Outreach email drafted for {target}. Subject: {result['subject']}",
            "action": "tool_result",
            "tool": "generate_email",
            "result": result,
            "suggestions": _page_suggestions(current_page, db_context),
        }

    if re.search(r"\b(generate|create|write)\b.*\bpitch\b", low):
        product = _safe_product_from_message(clean, "SalesSparkAI")
        target = _safe_audience_from_message(clean, "SaaS buyers")
        req = PitchRequest(product=product, target=target)
        result = generate_pitch(req)
        return {
            "response": f"Sales pitch generated for {product} targeting {target}.",
            "action": "tool_result",
            "tool": "generate_pitch",
            "result": result,
            "suggestions": _page_suggestions(current_page, db_context),
        }

    if re.search(r"\b(analy[sz]e|review|check)\b.*\bleads?\b", low):
        top = db_context.get("top_leads", [])
        top_line = ""
        if top:
            lead = top[0]
            top_line = f" Top lead: {lead['company']} ({lead['score']}/100, {lead['category']})."
        return {
            "response": _pipeline_brief(db_context) + top_line,
            "action": "tool_result",
            "tool": "analyze_leads",
            "result": {
                "pipeline": db_context,
                "top_lead": top[0] if top else None,
            },
            "suggestions": _page_suggestions(current_page, db_context),
        }

    return None


def _lead_intelligence_from_message(message: str, current_page: str, db_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    low = message.lower()
    top = db_context.get("top_leads", [])
    top_lead = top[0] if top else None

    if re.search(r"\b(which|what)\b.*\blead\b.*\b(focus|prioriti[sz]e|target)\b", low):
        if not top_lead:
            return {
                "response": "No leads are available yet. Add leads first and I can prioritize the best opportunity.",
                "suggestions": _page_suggestions(current_page, db_context),
            }
        return {
            "response": (
                f"Your highest priority lead is {top_lead['company']} with a score of {top_lead['score']}. "
                "I recommend scheduling a product demo and leading with ROI benefits."
            ),
            "suggestions": _page_suggestions(current_page, db_context),
        }

    if "help me close more deals" in low or "close more deals" in low:
        actions = []
        if top_lead:
            actions.append(f"1. Prioritize {top_lead['company']} ({top_lead['score']}/100) for immediate contact.")
        actions.append("2. Generate personalized outreach for top hot and warm leads.")
        actions.append("3. Schedule day 1 / day 3 / day 7 follow-up sequence for warm leads.")
        actions.append("4. Use deal closure assistant to refine objection handling and next steps.")
        return {
            "response": "Here is a deal-closing workflow based on your current pipeline:\n" + "\n".join(actions),
            "action": "multi_step",
            "steps": actions,
            "suggestions": _page_suggestions(current_page, db_context),
        }

    if re.search(r"\b(how many|pipeline|hot leads|warm leads|cold leads|average score)\b", low):
        return {
            "response": _pipeline_brief(db_context),
            "suggestions": _page_suggestions(current_page, db_context),
        }

    return None


def _page_guidance_from_message(message: str, current_page: str) -> Optional[str]:
    if not re.search(r"\b(how do i|how to|guide me|what can i do here)\b", message.lower()):
        return None

    page = _normalize_page(current_page)
    if page == "tools":
        return "You are on the Tools page. Enter product and audience details, then run campaign, pitch, email, or social generators from each card."
    if page == "leads":
        return "You are on the Leads page. Review lead scores, then use Deal Closure Assistant and Follow-up Planner for prioritized actions."
    if page == "prediction":
        return "You are on the Prediction page. Choose platform and goal, run prediction, then use the reasoning and suggestions to improve campaign setup."
    if page == "market":
        return "You are on the Market Intelligence page. Select industry, region, and horizon, then analyze demand, competition, and opportunity outputs."
    if page == "sales_copilot":
        return "You are on the Sales Copilot page. Track KPI cards, inspect momentum and alerts, and use Next Best Actions to prioritize outreach."
    return None
@app.post("/chat")
def chat_assistant(req: ChatRequest):
    user_message = (req.message or "").strip()
    if not user_message:
        return {"error": "Message must not be empty."}

    db_context = get_pipeline_snapshot()
    current_page = req.current_page or "unknown"

    nav_page = _detect_navigation_intent(user_message)
    if nav_page:
        return {
            "response": f"Opening the {nav_page.replace('_', ' ').title()} page.",
            "action": "navigate",
            "page": nav_page,
            "url": NAVIGATION_URLS[nav_page],
            "suggestions": _page_suggestions(current_page, db_context),
        }

    tool_result = _tool_execution_from_message(user_message, current_page, db_context)
    if tool_result:
        return tool_result

    lead_intel = _lead_intelligence_from_message(user_message, current_page, db_context)
    if lead_intel:
        return lead_intel

    page_guidance = _page_guidance_from_message(user_message, current_page)
    if page_guidance:
        return {
            "response": page_guidance,
            "suggestions": _page_suggestions(current_page, db_context),
        }

    try:
        ai_result = generate_chat_response(
            message=user_message,
            db_context=db_context,
            current_page=current_page,
            history=req.history or [],
        )

        if ai_result.get("action") == "navigate":
            page = (ai_result.get("page") or "").lower()
            mapping = {
                "home": "home",
                "landing": "home",
                "index": "home",
                "index.html": "home",
                "copilot": "sales_copilot",
                "campaigns": "tools",
                "market": "market",
                "prediction": "prediction",
                "leads": "leads",
                "tools": "tools",
                "dashboard": "sales_copilot",
            }
            normalized_page = mapping.get(page, page)
            if normalized_page in NAVIGATION_URLS:
                ai_result["page"] = normalized_page
                ai_result["url"] = NAVIGATION_URLS[normalized_page]

        if "suggestions" not in ai_result:
            ai_result["suggestions"] = _page_suggestions(current_page, db_context)

        return ai_result

    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        logger.error("[CHAT] Groq error (%s): %s", type(exc).__name__, exc)
        return {
            "response": "I'm here to help with SalesSparkAI features like lead analysis, campaign generation, and sales strategy.",
            "suggestions": _page_suggestions(current_page, db_context),
        }


@app.get("/chat/test")
def chat_test():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"status": "error", "reason": "GROQ_API_KEY is empty. Check your .env file."}
    try:
        result = generate_chat_response(
            message="Hello, who are you?",
            db_context=get_pipeline_snapshot(),
            current_page="test",
            history=[],
        )
        return {
            "status": "ok",
            "api_key_prefix": api_key[:8] + "...",
            "model": "llama-3.3-70b-versatile",
            "test_response": result,
        }
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__, "error_detail": str(exc)}


@app.get("/health")
def health():
    return {"status": "SalesSpark AI Backend Running", "version": "4.0"}


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














