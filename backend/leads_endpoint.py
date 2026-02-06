# -------------------- 7B. GET ALL LEADS (FOR DROPDOWN) --------------------
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
