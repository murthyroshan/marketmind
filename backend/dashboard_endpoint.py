# -------------------- 7. DASHBOARD (REAL-TIME METRICS) --------------------
@app.get("/dashboard")
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    
    # Check real data availability
    cur.execute("SELECT COUNT(*) FROM campaigns")
    real_campaigns = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM leads")
    real_leads = cur.fetchone()[0]
    
    # DECISION: Use Real Data or Synthetic Data
    use_synthetic = (real_leads < MIN_LEADS_REQUIRED) or (real_campaigns == 0)
    
    if use_synthetic:
        # ============ SYNTHETIC DATA MODE ============
        data_source = "Simulated (Demo)"
        
        total_leads = len(DEMO_LEADS)
        hot_leads = sum(1 for lead in DEMO_LEADS if lead["category"] == "Hot")
        avg_lead_score = sum(lead["score"] for lead in DEMO_LEADS) / len(DEMO_LEADS)
        total_campaigns = sum(DEMO_CAMPAIGNS.values())
        
        # Best platform = platform with most campaigns in demo
        best_platform = max(
            ["LinkedIn", "Instagram", "Email"],
            key=lambda p: DEMO_CAMPAIGNS.get(p.lower(), 0)
        )
        
        # Trend: compare first half vs second half of demo leads
        mid = len(DEMO_LEADS) // 2
        recent_avg = sum(lead["score"] for lead in DEMO_LEADS[mid:]) / mid
        older_avg = sum(lead["score"] for lead in DEMO_LEADS[:mid]) / mid
        
        print(f"[DASHBOARD] Using SYNTHETIC data")
    else:
        # ============ REAL DATA MODE ============
        data_source = "Live Database"
        
        total_leads = real_leads
        total_campaigns = real_campaigns
        
        cur.execute("SELECT COUNT(*) FROM leads WHERE category='Hot'")
        hot_leads = cur.fetchone()[0]
        
        cur.execute("SELECT AVG(score) FROM leads")
        avg_lead_score = cur.fetchone()[0] or 0
        
        # Best platform: platform with highest avg lead score
        cur.execute("""
            SELECT c.platform, AVG(l.score) as avg_score
            FROM campaigns c
            LEFT JOIN leads l ON l.created_at >= c.created_at
            GROUP BY c.platform
            ORDER BY avg_score DESC
            LIMIT 1
        """)
        best_row = cur.fetchone()
        best_platform = best_row[0] if best_row else "LinkedIn"
        
        # Trend: compare recent 5 leads vs older 5 leads
        cur.execute("""
            SELECT score FROM leads 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_scores = [row[0] for row in cur.fetchall()]
        
        cur.execute("""
            SELECT score FROM leads 
            ORDER BY created_at ASC 
            LIMIT 5
        """)
        older_scores = [row[0] for row in cur.fetchall()]
        
        recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        older_avg = sum(older_scores) / len(older_scores) if older_scores else 0
        
        print(f"[DASHBOARD] Using REAL data")
    
    conn.close()
    
    # Compute trend
    trend_diff = recent_avg - older_avg
    if trend_diff > 10:
        lead_quality_trend = "Improving"
    elif trend_diff < -10:
        lead_quality_trend = "Declining"
    else:
        lead_quality_trend = "Stable"
    
    return {
        "data_source": data_source,
        "metrics": {
            "total_leads": total_leads,
            "hot_leads": hot_leads,
            "avg_lead_score": round(avg_lead_score, 1),
            "total_campaigns": total_campaigns,
            "best_platform": best_platform,
            "lead_quality_trend": lead_quality_trend
        }
    }
