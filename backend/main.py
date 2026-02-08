from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime

import random

# Initialize FastAPI
app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection helper
def get_db():
    return sqlite3.connect("backend/sales.db")

# Initialize Database Tables
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Create campaigns table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        platform TEXT,
        goal TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create leads table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT,
        budget INTEGER,
        interest INTEGER,
        score INTEGER,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Seed Data if empty
    cur.execute("SELECT COUNT(*) FROM leads")
    count = cur.fetchone()[0]
    
    if count == 0:
        print("[INFO] Seeding realistic demo data...")
        companies = ["TechCorp", "Innovate Ltd", "BlueSky Inc", "Quantum Systems", "Nexus AI", 
                     "Alpha Solutions", "CyberDyan", "Global Tech", "FutureSoft", "DataFlow",
                     "SmartComm", "EcoEnergy", "FinTech Pro", "MediCare Plus", "EduLearning"]
        
        for i, company in enumerate(companies):
            # 2 Hot, 5 Warm, 8 Cold
            if i < 2:
                score = random.randint(80, 95)
                category = "Hot"
                interest = random.randint(8, 10)
                budget = random.randint(50000, 100000)
            elif i < 7:
                score = random.randint(50, 79)
                category = "Warm"
                interest = random.randint(5, 8)
                budget = random.randint(10000, 40000)
            else:
                score = random.randint(15, 49)
                category = "Cold"
                interest = random.randint(1, 5)
                budget = random.randint(1000, 9000)
                
            cur.execute(
                "INSERT INTO leads (company, budget, interest, score, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (company, budget, interest, score, category, datetime.now().isoformat())
            )
        print("[INFO] Seeded 15 leads.")

    conn.commit()
    conn.close()
    print("[INFO] Database initialized (tables created if missing)")

# Initialize DB on startup
init_db()

# ==================== PYDANTIC MODELS ====================
class CampaignRequest(BaseModel):
    product: str
    platform: str
    goal: str

class PitchRequest(BaseModel):
    product: str
    target: str

class ScoreRequest(BaseModel):
    company: str
    budget: int
    interest: int

class AnalysisRequest(BaseModel):
    industry: str

class EmailRequest(BaseModel):
    recipient: str
    context: str
    product: str

class ContentRequest(BaseModel):
    product: str
    platform: str

class WhatsAppRequest(BaseModel):
    recipient: str
    offer: str

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

# ==================== PHASE 1: CORE GENERATORS ====================

# 1. Campaign Generator
@app.post("/campaigns")
def generate_campaign(req: CampaignRequest):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO campaigns (product, platform, goal, created_at) VALUES (?, ?, ?, ?)",
        (req.product, req.platform, req.goal, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    return {
        "objective": f"Launch a high-impact {req.platform} campaign to drive {req.goal} for {req.product}.",
        "theme": "Authority & Trust Building",
        "cta": "Schedule Your Free Strategic Consultation",
        "outcome": "20-30% increase in qualified inbound leads within Q1.",
        "ai_insight": f"Data indicates {req.platform} algorithms are currently prioritizing educational content for {req.goal} campaigns."
    }

# 2. Sales Pitch Generator
@app.post("/pitch")
def generate_pitch(req: PitchRequest):
    return {
        "problem": f"{req.target} often face fragmented processes that kill team productivity and slow down revenue cycles.",
        "value_prop": f"{req.product} unifies your workflow, automating manual tasks to recover 15+ hours per week per rep.",
        "objection": "Implementation takes less than 24 hours with zero downtime, unlike legacy competitors.",
        "closing": "If we could show you a 3x ROI in the first month, would you be open to a 15-minute walkthrough?",
        "ai_insight": f"Emphasize speed to value—{req.target} care most about immediate efficiency gains right now."
    }

# 3. Lead Scoring
@app.post("/leads")
def score_lead(req: ScoreRequest):
    # Deterministic Scoring Logic
    score = 20 # Base Score
    
    # Budget Scoring (Max 40)
    if req.budget >= 50000: score += 40
    elif req.budget >= 10000: score += 30
    elif req.budget >= 5000: score += 15
    else: score += 5
    
    # Interest Scoring (Max 40)
    if req.interest >= 9: score += 40
    elif req.interest >= 7: score += 30
    elif req.interest >= 5: score += 15
    else: score += 5
    
    score = min(100, score)
    
    # Category Deterministic Logic
    if score >= 80:
        category = "Hot"
        recommendation = "Schedule a discovery call within 3 days" # Strict prompt output
    elif score >= 55: # Strict threshold 55-79
        category = "Warm"
        recommendation = "Send a personalized nurture email with a relevant case study"
    else:
        category = "Cold"
        recommendation = "Add to monthly newsletter for long-term brand awareness"
        
    explanation = f"Moderate interest ({req.interest}/10) combined with budget of ${req.budget} results in a {category} score."
    if category == "Hot":
        explanation = f"High interest ({req.interest}/10) and strong budget indicates immediate readiness."
    elif category == "Cold":
        explanation = f"Low interest ({req.interest}/10) suggests long-term nurturing is required."

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO leads (company, budget, interest, score, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (req.company, req.budget, req.interest, score, category, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return {
        "score": score,
        "category": category,
        "recommendation": recommendation,
        "explanation": explanation
    }

# 4. Market Analysis
@app.post("/market")
def market_analysis_tool(req: AnalysisRequest):
    return {
        "trend": "Rapid Upward Growth",
        "demand": "High Demand (85/100)",
        "competition": "Moderate Saturation",
        "opportunity": "Expansion into Enterprise Niche",
        "ai_insight": f"{req.industry} markets are currently rewarding vertical integration and specialized service providers."
    }

# 5. Channel Content Generator
@app.post("/social")
def generate_social(req: ContentRequest):
    return {
        "caption": f"Struggling to scale your operations? 🚀\n\n{req.product} empowers teams to break through bottlenecks and achieve predictable growth. Stop guessing and start scaling today.\n\n👇 Drop a comment for a free playbook.",
        "hashtags": f"#{req.product.replace(' ', '')} #{req.platform} #GrowthHacking #SaaS #Productivity",
        "ai_insight": f"Posts with questions in the first line see 2x higher engagement on {req.platform}."
    }

# 6. Personalized Email
@app.post("/email")
def generate_email(req: EmailRequest):
    recipient = req.recipient.strip()
    context = req.context.strip()
    product = req.product.strip()

    body = f"""Hi {recipient},

I noticed that teams dealing with {context} often struggle with manual follow-ups and low-quality engagement.

{product} helps automate outreach, prioritize high-intent leads, and improve response rates—without increasing workload.

Would you be open to a quick 10-minute conversation this week to see if this could help your team?

Best regards,
SalesSpark AI Team
"""

    return {
        "subject": f"Quick idea to improve your {context}",
        "body": body,
        "follow_up_tip": "If there’s no reply, send a short follow-up after 3 days referencing this email."
    }

# 7. AI Chatbot
# --- Session Management ---
SESSIONS = {}  # In-memory session store: {session_id: {history: [], last_intent: str, last_data: dict}}

# --- Helper: Get Real-Time Metrics ---
def get_sales_metrics():
    conn = get_db()
    cur = conn.cursor()
    
    # Leads
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
    hot_leads = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Warm'")
    warm_leads = cur.fetchone()[0]

    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    # Campaigns
    cur.execute("SELECT COUNT(*) FROM campaigns")
    total_campaigns = cur.fetchone()[0]

    # Pipeline Health
    if total_leads == 0:
        health = "Empty"
    elif hot_leads >= 3 and avg_score > 50:
        health = "Healthy"
    elif hot_leads == 0:
        health = "At Risk"
    else:
        health = "Needs Nurturing"

    conn.close()
    
    return {
        "total_leads": total_leads,
        "hot_leads": hot_leads,
        "warm_leads": warm_leads,
        "avg_score": round(avg_score, 1),
        "total_campaigns": total_campaigns,
        "pipeline_health": health
    }

# --- 7. AI Chatbot Endpoint (Upgraded) ---
@app.post("/chat")
def chat_assistant(req: ChatRequest):
    session_id = req.session_id
    msg = req.message.lower()
    
    # Initialize Session
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {"history": [], "last_intent": None, "context_data": {}}
    
    session = SESSIONS[session_id]
    metrics = get_sales_metrics()
    
    response_text = ""
    follow_up = ""
    suggestions = []
    current_intent = "general"

    # --- INTENT LOGIC ---

    # 1. LEADS & FOCUS
    if any(k in msg for k in ["focus", "prioritize", "start", "lead"]):
        current_intent = "leads_focus"
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, company, category, score FROM leads ORDER BY score DESC LIMIT 3")
        top_leads = cur.fetchall()
        conn.close()
        
        if not top_leads:
            response_text = "Your lead list is currently empty. I can't recommend a focus until we generate some leads."
            follow_up = "Should I simulate some demo leads for you?"
            suggestions = ["Generate demo leads", "How does scoring work?", "Campaign strategy"]
        else:
            lead_details = ", ".join([f"Lead #{l[0]} ({l[1]}, {l[3]}/100)" for l in top_leads])
            response_text = f"Based on score and intent, your top priorities are: {lead_details}. These have the highest probability of closing this week."
            follow_up = "Would you like a closing strategy for the top lead?"
            suggestions = ["Get closing strategy", "Draft email to Lead #1", "Pipeline health"]
            
            # Store for context
            session["context_data"]["top_lead_id"] = top_leads[0][0]

    # 2. PIPELINE HEALTH & RISKS
    elif any(k in msg for k in ["health", "pipeline", "risk", "status"]):
        current_intent = "pipeline_health"
        
        if metrics["pipeline_health"] == "At Risk":
            response_text = f"⚠️ **Alert:** Your pipeline is At Risk. You have 0 Hot leads and an average score of {metrics['avg_score']}. You need to refill the top of the funnel immediately."
            follow_up = "Shall I recommend a lead generation campaign?"
            suggestions = ["Generate campaign", "Why is score low?", "Show all leads"]
        elif metrics["pipeline_health"] == "Empty":
            response_text = "Your pipeline is empty. We need to launch campaigns to generate initial data."
            follow_up = "Ready to create your first campaign?"
            suggestions = ["Create campaign", "Run simulation", "Market trends"]
        else:
            response_text = f"✅ **Healthy:** You have {metrics['hot_leads']} Hot leads and {metrics['warm_leads']} Warm leads. Average lead quality is {metrics['avg_score']}/100."
            follow_up = "Do you want to focus on closing the hot leads?"
            suggestions = ["Closing tips", "Nurture warm leads", "Market analysis"]

    # 3. EXPLAIN / WHY (Context Aware)
    elif any(k in msg for k in ["why", "explain", "reason", "how"]):
        last_intent = session.get("last_intent")
        
        if last_intent == "leads_focus":
            response_text = "I prioritized those leads because they combine high Budget fit (> $50k) with strong Intent signals (web visits, email opens). In our model, Score = Budget(40%) + Interest(40%) + Baseline(20%)."
            follow_up = "Want to see the full score breakdown?"
            suggestions = ["Score breakdown", "Contact Lead #1", "Next actions"]
        elif last_intent == "pipeline_health":
            response_text = f"I flagged the pipeline because 'Hot Leads' (Score > 80) are the strongest predictor of revenue. You currently have {metrics['hot_leads']}, and our target is at least 3."
            follow_up = "Should we draft a campaign to fix this?"
        else:
            response_text = "I base my recommendations on your real-time database metrics: Lead Scores, Campaign Performance, and Pipeline Volume. I look for the path of highest revenue probability."
            follow_up = "Ask me to analyze your top lead."
            suggestions = ["Analyze top lead", "Pipeline summary", "Campaign ideas"]

    # 4. CAMPAIGNS & STRATEGY
    elif any(k in msg for k in ["strategy", "campaign", "marketing", "grow"]):
        current_intent = "marketing_strategy"
        response_text = f"You currently have {metrics['total_campaigns']} active campaigns. To grow, I recommend a 'Competitor Conquesting' campaign on LinkedIn to target dissatisfied users in your sector."
        follow_up = "Do you want me to draft the ad copy?"
        suggestions = ["Draft ad copy", "Predict campaign ROI", "Analyze market"]

    # 5. GENERAL / GREETING
    else:
        response_text = f"I'm your SalesSpark Analyst. I track your {metrics['total_leads']} leads and {metrics['total_campaigns']} campaigns in real-time."
        follow_up = "Ask me: 'Who should I call today?' or 'How is my pipeline?'"
        suggestions = ["Who to call?", "Pipeline risks", "Draft cold email"]

    # Update Session
    session["history"].append({"user": msg, "bot": response_text})
    session["last_intent"] = current_intent
    
    return {
        "reply": response_text,
        "follow_up": follow_up,
        "suggestions": suggestions
    }

# ... (Existing Request Models)

class MarketAnalysisRequest(BaseModel):
    industry: str
    region: str = "Global"
    time_horizon: str = "Mid"  # Short, Mid, Long

# ... (Existing Endpoints)

@app.post("/market/analyze")
def market_intelligence_analysis(req: MarketAnalysisRequest):
    industry = req.industry.lower()
    region = req.region
    horizon = req.time_horizon

    # 1. INDUSTRY BASELINES
    baselines = {
        "saas":       {"demand": 80, "comp": 85, "opp": 60, "channel": {"LinkedIn": 90, "Email": 70, "Instagram": 40}},
        "finance":    {"demand": 65, "comp": 90, "opp": 55, "channel": {"LinkedIn": 85, "Email": 85, "Instagram": 20}},
        "technology": {"demand": 75, "comp": 70, "opp": 70, "channel": {"LinkedIn": 80, "Email": 60, "Instagram": 50}},
        "healthcare": {"demand": 85, "comp": 60, "opp": 85, "channel": {"LinkedIn": 50, "Email": 95, "Instagram": 30}},
        "ecommerce":  {"demand": 60, "comp": 80, "opp": 40, "channel": {"LinkedIn": 30, "Email": 60, "Instagram": 95}},
    }
    
    # Fallback/Default
    base = baselines.get(industry, baselines["saas"])

    # 2. REGION MULTIPLIERS
    reg_mult = {
        "Global":        {"demand": 1.0,  "comp": 1.0},
        "North America": {"demand": 1.2,  "comp": 1.3}, 
        "Europe":        {"demand": 1.1,  "comp": 1.2},
        "APAC":          {"demand": 1.35, "comp": 1.1}, # Asia Pacific
        "NA":            {"demand": 1.2,  "comp": 1.3}, # Handling code differences
        "EU":            {"demand": 1.1,  "comp": 1.2},
    }
    r_factor = reg_mult.get(region, reg_mult["Global"])

    # 3. TIME HORIZON MULTIPLIERS
    # specific impact on Demand and Opportunity
    time_mult = {
        "Short": {"demand": 0.85, "opp": 0.7, "curve": "flat"},
        "Mid":   {"demand": 1.0,  "opp": 1.0, "curve": "linear"},
        "Long":  {"demand": 1.3,  "opp": 1.5, "curve": "exponential"}
    }
    t_factor = time_mult.get(horizon, time_mult["Mid"])

    # 4. CALCULATE FINAL SCORES (Clamped 0-100)
    final_demand = min(100, max(0, base["demand"] * r_factor["demand"] * t_factor["demand"]))
    final_comp = min(100, max(0, base["comp"] * r_factor["comp"]))
    final_opp = min(100, max(0, base["opp"] * t_factor["opp"]))
    
    saturation = (final_comp + (100 - final_opp)) / 2

    # 5. GENERATE TREND CURVE
    demand_trend = []
    points = 6
    
    if t_factor["curve"] == "flat": # Short term: Volatile/Flat
        current = final_demand
        for i in range(points):
            noise = random.randint(-8, 8)
            demand_trend.append(min(100, max(0, current + noise)))
            
    elif t_factor["curve"] == "linear": # Mid term: Steady growth
        start = final_demand * 0.8
        step = (final_demand * 1.1 - start) / points
        for i in range(points):
            val = start + (step * i) + random.randint(-2, 2)
            demand_trend.append(min(100, max(0, val)))
            
    else: # Long term: Exponential
        start = final_demand * 0.6
        growth_rate = 1.15 if industry == "healthcare" and region in ["APAC", "Asia Pacific"] else 1.1
        for i in range(points):
            val = start * (growth_rate ** i)
            demand_trend.append(min(100, max(0, val)))

    # 6. DYNAMIC INSIGHT GENERATION
    insight_tone = "neutral"
    if final_opp > 75: insight_tone = "positive"
    elif final_comp > 80: insight_tone = "cautious"
    
    if insight_tone == "positive":
        insight = f"🚀 **High-Growth Opportunity:** {req.industry} in {req.region} is showing explosive potential over the {req.time_horizon} term. With demand at {(final_demand):.0f}/100 and opportunity at {(final_opp):.0f}/100, this is a prime market for aggressive expansion. Competitive pressure is manageable."
    elif insight_tone == "cautious":
        insight = f"⚠️ **Saturated Market:** {req.industry} in {req.region} is heavily contested (Competition: {(final_comp):.0f}/100). While demand is present ({(final_demand):.0f}/100), costs of acquisition will be high. Differentiate via niche positioning rather than broad targeting."
    else:
        insight = f"⚖️ **Stable Market:** {req.industry} in {req.region} shows steady, predictable behavior. Demand is moderate ({(final_demand):.0f}/100). Focus on operational efficiency and customer retention."

    if industry == "healthcare" and region in ["APAC", "Asia Pacific"] and horizon == "Long":
        insight = "🔥 **Strategic Unicorn Logic:** Healthcare in Asia-Pacific shows explosive long-term demand with low competitive pressure. This is a rare high-opportunity market. Early positioning and compliance-focused branding will deliver outsized returns over 24-36 months."

    return {
        "insight": insight,
        "demand_trend": demand_trend,
        "market_matrix": {
            "competition": round(final_comp),
            "opportunity": round(final_opp),
            "saturation": round(saturation)
        },
        "channels": base["channel"],
        "meta": {
             "industry": req.industry,
             "horizon": req.time_horizon,
             "scores": {"d": final_demand, "c": final_comp, "o": final_opp}
        }
    }

# ==================== PHASE 2: INTELLIGENCE ENDPOINTS ====================

# 7. Dashboard
@app.get("/dashboard")
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM campaigns")
    total_campaigns = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    use_synthetic = (total_leads < 10) or (total_campaigns == 0)
    
    if use_synthetic:
        data_source = "Simulated (Demo)"
        metrics = {
            "total_leads": 20,
            "hot_leads": 5,
            "avg_lead_score": 56.5,
            "total_campaigns": 12,
            "best_platform": "LinkedIn",
            "lead_quality_trend": "Stable"
        }
    else:
        cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
        hot_leads = cur.fetchone()[0]
        
        cur.execute("SELECT AVG(score) FROM leads")
        avg_score = cur.fetchone()[0] or 0
        
        cur.execute("SELECT platform, COUNT(*) as cnt FROM campaigns GROUP BY platform ORDER BY cnt DESC LIMIT 1")
        platform_row = cur.fetchone()
        best_platform = platform_row[0] if platform_row else "N/A"
        
        data_source = "Live Database"
        metrics = {
            "total_leads": total_leads,
            "hot_leads": hot_leads,
            "avg_lead_score": round(avg_score, 1),
            "total_campaigns": total_campaigns,
            "best_platform": best_platform,
            "lead_quality_trend": "Improving" if avg_score > 60 else "Stable"
        }
    
    conn.close()
    return {"data_source": data_source, "metrics": metrics}

# 7B. GET ALL LEADS (FOR DROPDOWN)
@app.get("/leads")
def get_all_leads():
    """Fetch all leads for dropdown selection"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT id, category, score FROM leads ORDER BY score DESC")
    rows = cur.fetchall()
    conn.close()
    
    leads = [{"id": row[0], "category": row[1], "score": row[2]} for row in rows]
    return {"leads": leads}

# 8. Campaign Prediction
@app.post("/predict/campaign")
def predict_campaign(req: PredictionRequest):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
    hot_leads = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM campaigns WHERE platform=?", (req.platform,))
    platform_campaigns = cur.fetchone()[0]
    
    conn.close()
    
    use_synthetic = (total_leads < 5) or (platform_campaigns == 0)
    
    if use_synthetic:
        data_source = "Simulated (Demo)"
        avg_score = 58.0
        total_leads = 20
        hot_leads = 5
        platform_campaigns = 3
    else:
        data_source = "Live Database"
    
    engagement_base = 40 + (avg_score * 0.6)
    if platform_campaigns == 0:
        engagement_base -= 10
    
    engagement_prob = int(max(30, min(90, engagement_base)))
    conversion_prob = round(engagement_prob * 0.15)
    
    if platform_campaigns == 0:
        risk = "High"
    elif avg_score >= 60:
        risk = "Low"
    else:
        risk = "Medium"
    
    explanation = f"Based on {total_leads} leads (avg: {avg_score:.1f}/100) and {platform_campaigns} {req.platform} campaigns. {risk} risk."
    
    return {
        "engagement_prob": engagement_prob,
        "conversion_prob": conversion_prob,
        "risk_level": risk,
        "data_source": data_source,
        "metrics_used": {
            "total_leads": total_leads,
            "avg_lead_score": round(avg_score, 1),
            "platform_campaigns": platform_campaigns,
            "hot_leads": hot_leads
        },
        "explanation": explanation
    }

# 9. Recommendations
@app.get("/recommendations")
def recommendations():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
    hot_leads = cur.fetchone()[0]
    
    cur.execute("SELECT platform, COUNT(*) as cnt FROM campaigns GROUP BY platform ORDER BY cnt DESC LIMIT 1")
    row = cur.fetchone()
    best_platform = row[0] if row else "LinkedIn"
    
    conn.close()
    
    if avg_score < 50:
        action = "Focus on lead quality improvement"
        tip = "Current average score is below 50. Implement better targeting and qualification criteria."
    elif hot_leads < 5:
        action = "Increase hot lead pipeline"
        tip = f"Only {hot_leads} hot leads in pipeline. Launch targeted campaigns on {best_platform}."
    else:
        action = "Optimize conversion process"
        tip = f"Strong pipeline detected. Focus on closing hot leads and scaling {best_platform} campaigns."
    
    return {
        "action": action,
        "tip": tip,
        "platform": best_platform
    }

# 10. Segments
@app.get("/segments")
def segments():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80")
    high_value = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE interest >= 8")
    high_intent = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE budget < 20000")
    price_sensitive = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE score < 40")
    low_intent = cur.fetchone()[0]
    
    conn.close()
    
    return {
        "high_value": high_value,
        "high_intent": high_intent,
        "price_sensitive": price_sensitive,
        "low_intent": low_intent
    }

# 11. Weekly Report
@app.get("/weekly-report")
def weekly_report():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
    hot_leads = cur.fetchone()[0]
    
    conn.close()
    
    summary = f"This week: {total_leads} total leads with {hot_leads} hot prospects. Average lead quality: {avg_score:.0f}/100. "
    
    if hot_leads >= 5:
        summary += "Strong pipeline — prioritize immediate outreach to hot leads."
    elif avg_score < 50:
        summary += "Lead quality below target — review targeting criteria."
    else:
        summary += "Moderate pipeline — continue nurturing warm leads."
    
    return {
        "summary": summary,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# ==================== PHASE 3: SALES ACTION COPILOT ====================

# 12. Next-Best-Action Engine (DYNAMIC)
@app.get("/actions/next")
def next_actions():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, score, interest, category, created_at
        FROM leads
        ORDER BY (score * 0.7 + interest * 3.0) DESC
        LIMIT 5
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return {
            "actions": [],
            "message": "No leads available. Generate leads to see prioritized actions."
        }
    
    actions = []
    for row in rows:
        lead_id, score, interest, category, created_at = row
        
        if score >= 80:
            action = "🔥 Call immediately — high close probability"
            reason = f"Score {score}/100, ready to close"
        elif score >= 60:
            action = "📧 Send follow-up email with ROI case study"
            reason = f"Score {score}/100, interest {interest}/10 — strong engagement"
        elif score >= 45 and interest >= 7:
            action = "📞 Schedule discovery call"
            reason = f"Score {score}/100 with high interest ({interest}/10)"
        elif score >= 35:
            action = "🧠 Send value-based insight email"
            reason = f"Score {score}/100 — build credibility first"
        else:
            action = "⏳ Deprioritize — monitor for future intent"
            reason = f"Score {score}/100, low priority"
        
        priority_score = round(score * 0.7 + interest * 3.0, 1)
        
        actions.append({
            "lead_id": lead_id,
            "category": category,
            "action": action,
            "reason": reason,
            "score": score,
            "priority_score": priority_score
        })
    
    return {"actions": actions}

# 13. Sales Trend Intelligence
@app.get("/trends/sales")
def sales_trends():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    if total_leads < 5:
        conn.close()
        return {
            "trend": "insufficient",
            "trend_direction": "Insufficient data - add more leads",
            "risk_flags": [],
            "opportunity_flags": [{"alert": "Build your pipeline to unlock trend analysis", "reason": f"Only {total_leads} leads"}],
            "reason": f"Only {total_leads} leads. Need at least 5 for trend analysis."
        }
    
    window_size = min(7, total_leads // 2)
    
    cur.execute(f"SELECT score FROM leads ORDER BY created_at DESC LIMIT {window_size}")
    recent_scores = [row[0] for row in cur.fetchall()]
    
    cur.execute(f"SELECT score FROM leads ORDER BY created_at ASC LIMIT {window_size}")
    older_scores = [row[0] for row in cur.fetchall()]
    
    recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
    older_avg = sum(older_scores) / len(older_scores) if older_scores else 0
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80")
    hot_count = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    conn.close()
    
    trend_diff = recent_avg - older_avg
    if trend_diff > 10:
        trend = "improving"
        trend_direction = f"↑ Lead quality up {trend_diff:.0f} points"
        trend_reason = f"Recent {window_size} leads avg {recent_avg:.1f} vs older {window_size} avg {older_avg:.1f}"
    elif trend_diff < -10:
        trend = "declining"
        trend_direction = f"↓ Lead quality down {abs(trend_diff):.0f} points"
        trend_reason = f"Recent {window_size} leads avg {recent_avg:.1f} vs older {window_size} avg {older_avg:.1f}"
    else:
        trend = "stable"
        trend_direction = f"→ Consistent lead quality"
        trend_reason = f"Recent avg {recent_avg:.1f} ~= older avg {older_avg:.1f} (diff: {trend_diff:.1f})"
    
    risk_flags = []
    if hot_count == 0 and total_leads > 5:
        risk_flags.append({
            "alert": "⚠️ No hot leads in pipeline",
            "reason": f"0 Hot leads out of {total_leads} total"
        })
    if avg_score < 50:
        risk_flags.append({
            "alert": "⚠️ Average lead quality below target",
            "reason": f"Current avg score: {avg_score:.1f}/100 (target: 50+)"
        })
    if trend == "declining":
        risk_flags.append({
            "alert": "⚠️ Quality trending downward",
            "reason": f"Recent leads {trend_diff:.0f} points lower than older leads"
        })
    
    opportunity_flags = []
    if hot_count >= 5:
        opportunity_flags.append({
            "alert": "🎯 Strong pipeline - prioritize closures",
            "reason": f"{hot_count} Hot leads ready for immediate action"
        })
    if trend == "improving":
        opportunity_flags.append({
            "alert": "📈 Quality improving - scale campaigns",
            "reason": f"Lead quality up {trend_diff:.0f} points - campaigns are working"
        })
    
    return {
        "trend": trend,
        "trend_direction": trend_direction,
        "trend_reason": trend_reason,
        "risk_flags": risk_flags,
        "opportunity_flags": opportunity_flags,
        "metrics": {
            "total_leads": total_leads,
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1),
            "hot_leads": hot_count,
            "avg_score": round(avg_score, 1)
        }
    }

# 14. Real-Time Alerts
@app.get("/alerts")
def get_alerts():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80")
    hot_leads = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score_result = cur.fetchone()[0]
    avg_score = avg_score_result if avg_score_result else 0
    
    cur.execute("SELECT COUNT(*) FROM leads")
    recent_count = cur.fetchone()[0]
    
    conn.close()
    
    alerts = []
    
    if hot_leads == 0:
        alerts.append({
            "level": "warning",
            "message": "⚠️ No hot leads in pipeline",
            "reason": f"0 leads with score ≥ 80"
        })
    
    if avg_score < 50:
        alerts.append({
            "level": "warning",
            "message": "⚠️ Average lead quality below target",
            "reason": f"Current avg score: {avg_score:.1f}/100 (target: 50+)"
        })
    
    if recent_count < 3:
        alerts.append({
            "level": "info",
            "message": "📊 Low recent inbound activity",
            "reason": f"Only {recent_count} leads in database"
        })
    
    return {"alerts": alerts}

# 15. Deal Closure Assistant
@app.post("/deal/assist")
def deal_assist(req: DealAssistRequest):
    lead_id = req.lead_id
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT score, budget, interest, category FROM leads WHERE id = ?", (lead_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"error": f"Lead ID {lead_id} not found"}
    
    score, budget, interest, category = row
    
    if score >= 70 and budget >= 50000:
        closing_strategy = "Executive ROI-driven close"
        objection_focus = "ROI and long-term value"
    elif score >= 60 and budget >= 30000:
        closing_strategy = "Value-based competitive close"
        objection_focus = "Feature comparison and pricing"
    elif score >= 50:
        closing_strategy = "Consultative relationship-building"
        objection_focus = "Trust and implementation support"
    else:
        closing_strategy = "Nurture-first soft approach"
        objection_focus = "Education and use case alignment"
    
    if score >= 80:
        discount_range = "0–5%"
    elif score >= 60:
        discount_range = "5–10%"
    elif score >= 40:
        discount_range = "10–15%"
    else:
        discount_range = "15–20% (nurture pricing)"
    
    urgency_mapping = {"Hot": "High", "Warm": "Medium", "Cold": "Low"}
    urgency_level = urgency_mapping.get(category, "Medium")
    
    explanation = f"Score={score}, Budget=${budget:,}, Interest={interest}/10, Category={category}. Strategy tailored to lead profile."
    
    return {
        "closing_strategy": closing_strategy,
        "discount_range": discount_range,
        "objection_focus": objection_focus,
        "urgency_level": urgency_level,
        "explanation": explanation
    }

# 16. Follow-up Planner
@app.post("/followup/plan")
def followup_plan(req: FollowupRequest):
    lead_id = req.lead_id
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT category, score FROM leads WHERE id = ?", (lead_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"error": f"Lead ID {lead_id} not found"}
    
    category, score = row
    
    if category == "Hot":
        plan = {
            "day 1": "Call lead immediately - high close probability",
            "day 2": "Send detailed proposal with ROI breakdown",
            "day 3": "Follow-up call to address questions and close"
        }
        note = "Hot lead sequence optimized for fast closure"
    elif category == "Warm":
        plan = {
            "day 1": "Send personalized email with value proposition",
            "day 3": "Share relevant case study",
            "day 7": "Follow-up call to discuss next steps"
        }
        note = "Warm lead sequence focused on building trust"
    else:
        plan = {
            "day 3": "Send educational content",
            "day 7": "Share industry insights",
            "day 14": "Soft check-in to gauge interest"
        }
        note = "Cold lead sequence for gentle nurturing"
    
    return {
        "category": category,
        "score": score,
        "plan": plan,
        "note": note
    }

# Health check
@app.get("/")
def root():
    return {"status": "SalesSpark AI Backend Running", "version": "3.0"}
