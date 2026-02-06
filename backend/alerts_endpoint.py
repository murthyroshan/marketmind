# -------------------- ALERTS ENDPOINT (REAL-TIME) --------------------
@app.get("/alerts")
def get_alerts():
    conn = get_db()
    cur = conn.cursor()
    
    # Get metrics
    cur.execute("SELECT COUNT(*) FROM leads WHERE score >= 80")
    hot_leads = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(score) FROM leads")
    avg_score_result = cur.fetchone()[0]
    avg_score = avg_score_result if avg_score_result else 0
    
    # Recent leads (last 7 days - approximate using most recent leads)
    cur.execute("SELECT COUNT(*) FROM leads ORDER BY created_at DESC LIMIT 3")
    recent_count = cur.fetchone()[0]
    
    conn.close()
    
    # DYNAMIC ALERT GENERATION
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
