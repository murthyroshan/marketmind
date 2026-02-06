# ==================== PHASE 3: SALES ACTION COPILOT ====================

# -------------------- 11. DEAL CLOSURE ASSISTANT --------------------
@app.post("/deal/assist")
def deal_assist(data: dict):
    lead_id = data.get("lead_id")
    
    conn = get_db()
    cur = conn.cursor()
    
    # Fetch lead by ID
    cur.execute("SELECT score, budget, interest, category FROM leads WHERE id = ?", (lead_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"error": "Lead not found"}
    
    score, budget, interest, category = row
    
    # CLOSING STRATEGY LOGIC
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
    
    # DISCOUNT RANGE (inverse to score)
    if score >= 80:
        discount_range = "0–5%"
    elif score >= 60:
        discount_range = "5–10%"
    elif score >= 40:
        discount_range = "10–15%"
    else:
        discount_range = "15–20% (nurture pricing)"
    
    # URGENCY LEVEL (based on category)
    urgency_mapping = {"Hot": "High", "Warm": "Medium", "Cold": "Low"}
    urgency_level = urgency_mapping.get(category, "Medium")
    
    explanation = f"Score={score}, Budget=${budget}, Interest={interest}/10, Category={category}. Strategy tailored to lead profile."
    
    return {
        "closing_strategy": closing_strategy,
        "discount_range": discount_range,
        "objection_focus": objection_focus,
        "urgency_level": urgency_level,
        "explanation": explanation
    }

# -------------------- 12. NEXT-BEST-ACTION ENGINE --------------------
@app.get("/actions/next")
def next_actions():
    conn = get_db()
    cur = conn.cursor()
    
    # Fetch all leads with priority calculation
    cur.execute("""
        SELECT id, score, interest, category, budget
        FROM leads
        ORDER BY 
            CASE category 
                WHEN 'Hot' THEN 3 
                WHEN 'Warm' THEN 2 
                ELSE 1 
            END DESC,
            score DESC,
            interest DESC
        LIMIT 5
    """)
    
    rows = cur.fetchall()
    conn.close()
    
    actions = []
    for row in rows:
        lead_id, score, interest, category, budget = row
        
        # ACTION DETERMINATION
        if category == "Hot":
            action = f"🔥 Call today - High conversion probability (Score: {score})"
        elif category == "Warm" and interest >= 7:
            action = f"📧 Send follow-up email with case study"
        elif category == "Warm":
            action = f"📞 Schedule discovery call"
        else:
            action = f"🌱 Nurture with educational content"
        
        actions.append({
            "lead_id": lead_id,
            "action": action,
            "priority": category,
            "score": score
        })
    
    return {"actions": actions}

# -------------------- 13. SALES TREND INTELLIGENCE --------------------
@app.get("/trends/sales")
def sales_trends():
    conn = get_db()
    cur = conn.cursor()
    
    # Get total leads count
    cur.execute("SELECT COUNT(*) FROM leads")
    total_leads = cur.fetchone()[0]
    
    if total_leads < 10:
        # Use synthetic data
        return {
            "trend": "stable",
            "trend_direction": "Demo data - insufficient history",
            "risk_flags": [],
            "opportunity_flags": ["Build your pipeline to unlock trend analysis"]
        }
    
    # Compare recent vs older leads
    cur.execute("SELECT score FROM leads ORDER BY created_at DESC LIMIT 7")
    recent_scores = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT score FROM leads ORDER BY created_at ASC LIMIT 7")
    older_scores = [row[0] for row in cur.fetchall()]
    
    recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
    older_avg = sum(older_scores) / len(older_scores) if older_scores else 0
    
    # Hot leads count
    cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
    hot_count = cur.fetchone()[0]
    
    # Avg score
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score = cur.fetchone()[0] or 0
    
    conn.close()
    
    # TREND DETECTION
    trend_diff = recent_avg - older_avg
    if trend_diff > 10:
        trend = "improving"
        trend_direction = f"Lead quality up {trend_diff:.0f} points"
    elif trend_diff < -10:
        trend = "declining"
        trend_direction = f"Lead quality down {abs(trend_diff):.0f} points"
    else:
        trend = "stable"
        trend_direction = "Consistent lead quality"
    
    # RISK FLAGS
    risk_flags = []
    if hot_count == 0 and total_leads > 5:
        risk_flags.append("⚠️ No hot leads in pipeline")
    if avg_score < 40:
        risk_flags.append("⚠️ Average lead quality below target")
    if trend == "declining":
        risk_flags.append("⚠️ Quality trending downward")
    
    # OPPORTUNITY FLAGS
    opportunity_flags = []
    if hot_count >= 5:
        opportunity_flags.append("🎯 Strong pipeline - prioritize closures")
    if trend == "improving":
        opportunity_flags.append("📈 Quality improving - scale campaigns")
    
    return {
        "trend": trend,
        "trend_direction": trend_direction,
        "risk_flags": risk_flags,
        "opportunity_flags": opportunity_flags,
        "metrics": {
            "recent_avg": round(recent_avg, 1),
            "older_avg": round(older_avg, 1),
            "hot_leads": hot_count
        }
    }

# -------------------- 14. FOLLOW-UP PLANNER --------------------
@app.post("/followup/plan")
def followup_plan(data: dict):
    lead_id = data.get("lead_id")
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT category, score FROM leads WHERE id = ?", (lead_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return {"error": "Lead not found"}
    
    category, score = row
    
    # FOLLOW-UP SEQUENCE BY CATEGORY
    if category == "Hot":
        plan = {
            "day_1": "📞 Call immediately - high urgency",
            "day_2": "📄 Send tailored proposal with ROI breakdown",
            "day_3": "🤝 Schedule closing call or demo"
        }
    elif category == "Warm":
        plan = {
            "day_1": "📧 Send personalized email with value proposition",
            "day_3": "📊 Share case study or success story",
            "day_7": "📞 Follow-up call to discuss next steps"
        }
    else:  # Cold
        plan = {
            "day_3": "📧 Send educational content (blog/guide)",
            "day_7": "📚 Share industry insights or whitepaper",
            "day_14": "📞 Soft check-in call (no pressure)"
        }
    
    return {
        "lead_id": lead_id,
        "category": category,
        "score": score,
        "plan": plan,
        "note": f"Sequence optimized for {category} leads"
    }
