const API_BASE = "http://127.0.0.1:8000";

function showOutput(elementId, content, insight = "") {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.innerHTML = `
        ${content}
        ${insight ? `<div class="ai-insight"><b>AI Insight:</b> ${insight}</div>` : ''}
    `;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function generateCampaign() {
    const btn = document.querySelector('#campaigns button');
    const originalText = btn.innerText;
    btn.innerText = "Generating...";

    try {
        const payload = {
            product: document.getElementById('cG_product').value || "AI Solution",
            audience: document.getElementById('cG_audience').value || "Business Leaders",
            platform: document.getElementById('cG_platform').value,
            goal: document.getElementById('cG_goal').value
        };

        const res = await fetch(`${API_BASE}/campaigns`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        const content = `
            <strong>Objective:</strong> ${data.objective}<br>
            <strong>Campaign Theme:</strong> ${data.theme}<br>
            <strong>Marketing Strategy:</strong> ${data.marketing_strategy}<br>
            <strong>Messaging Approach:</strong> ${data.messaging_approach}<br>
            <strong>CTA:</strong> ${data.cta}<br>
            <strong>Expected Outcome:</strong> ${data.outcome}
        `;
        showOutput('cG_output', content, data.ai_insight);
    } catch (e) {
        alert("Backend Error: Ensure server is running!");
    } finally {
        btn.innerText = originalText;
    }
}

async function generatePitch() {
    const product = document.getElementById("pitchProduct").value;
    const target = document.getElementById("pitchTarget").value;

    try {
        const res = await fetch(`${API_BASE}/pitch`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product, target })
        });
        const data = await res.json();

        document.getElementById("pitchOutput").style.display = 'block';
        document.getElementById("pitchOutput").innerHTML = `
            <b>Opening Hook:</b> ${data.opening_hook}<br>
            <b>Problem Framing:</b> ${data.problem_framing}<br>
            <b>Product Positioning:</b> ${data.product_positioning}<br>
            <b>Objection Handling:</b> ${data.objection_handling}<br>
            <b>Closing Statement:</b> ${data.closing_statement}
        `;
    } catch (e) {
        document.getElementById("pitchOutput").style.display = 'block';
        document.getElementById("pitchOutput").innerHTML = `<b style='color:red'>Error: ${e.message}</b>`;
    }
}

async function scoreLead() {
    const company = document.getElementById("leadCompany").value;
    const budget = Number(document.getElementById("leadBudget").value);
    const interest = Number(document.getElementById("leadInterest").value);

    try {
        const res = await fetch(`${API_BASE}/leads`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ company, budget, interest })
        });
        const data = await res.json();

        document.getElementById("leadOutput").style.display = 'block';
        document.getElementById("leadOutput").innerHTML = `
            <b>Score:</b> ${data.score}/100<br>
            <b>Category:</b> ${data.category}<br>
            <b>Recommendation:</b> ${data.recommendation}<br>
            <b>Explanation:</b> ${data.explanation}
        `;
    } catch (e) {
        document.getElementById("leadOutput").style.display = 'block';
        document.getElementById("leadOutput").innerHTML = `<b style='color:red'>Error: ${e.message}</b>`;
    }
}

async function analyzeMarket() {
    try {
        const payload = { industry: document.getElementById('mA_industry').value || "Tech" };
        const res = await fetch(`${API_BASE}/market`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        const content = `
            <strong>Demand Insight:</strong> ${data.demand_insight || data.trend}<br>
            <strong>Demand Level:</strong> ${data.demand}<br>
            <strong>Competition Overview:</strong> ${data.competition_overview || data.competition}<br>
            <strong>Opportunity Summary:</strong> ${data.opportunity_summary || data.opportunity}
        `;
        showOutput('mA_output', content, data.ai_insight);
    } catch (e) {
        console.error(e);
    }
}

async function generateContent() {
    const product = document.getElementById("contentProduct").value;
    const platform = document.getElementById("contentPlatform").value;

    const res = await fetch(`${API_BASE}/social`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product, platform })
    });
    const data = await res.json();

    const output = document.getElementById("contentOutput");
    output.style.display = "block";
    output.innerHTML = `
        <h4>Generated Content</h4>
        <p><b>Tone:</b> ${data.tone}</p>
        <p><b>Caption:</b><br>${data.caption}</p>
        <p><b>Hashtags:</b> ${data.hashtags}</p>
        <p><i>${data.ai_insight}</i></p>
    `;
}

async function generateEmail() {
    const recipient = document.getElementById("emailRecipient").value;
    const context = document.getElementById("emailContext").value;
    const product = document.getElementById("emailProduct").value;

    const res = await fetch(`${API_BASE}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipient, context, product })
    });
    const data = await res.json();

    document.getElementById("emailOutput").style.display = 'block';
    document.getElementById("emailOutput").innerHTML = `
        <b>Subject:</b> ${data.subject}<br><br>
        <pre>${data.body}</pre><br>
        <i>${data.follow_up_tip}</i>
    `;
}

async function getDealStrategy() {
    const leadId = document.getElementById('deal_lead_id')?.value;
    if (!leadId) return;

    try {
        const res = await fetch(`${API_BASE}/deal/assist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: parseInt(leadId, 10) })
        });
        const data = await res.json();
        if (data.error) {
            showOutput('deal_output', data.error);
            return;
        }

        const output = `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 15px; color: var(--primary);">${data.closing_strategy}</div>
                <div style="margin-bottom: 12px;"><strong>Negotiation Advice:</strong> ${data.negotiation_advice || data.objection_focus}</div>
                <div style="margin-bottom: 12px;"><strong>Recommended Next Step:</strong> ${data.recommended_next_step || data.explanation}</div>
                <div style="margin-bottom: 12px;"><strong>Urgency:</strong> ${data.urgency_level}</div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 14px;"><strong>Reasoning:</strong> ${data.explanation}</div>
            </div>
        `;
        showOutput('deal_output', output);
    } catch (e) {
        showOutput('deal_output', "Backend Error: Ensure server is running!");
    }
}

async function getFollowupPlan() {
    const leadId = document.getElementById('followup_lead_id')?.value;
    if (!leadId) return;

    try {
        const res = await fetch(`${API_BASE}/followup/plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: parseInt(leadId, 10) })
        });
        const data = await res.json();
        if (data.error) {
            showOutput('followup_output', data.error);
            return;
        }
        const planSteps = Object.entries(data.plan).map(([day, action]) => `
            <div style="margin-bottom: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <strong style="color: var(--primary);">${day.toUpperCase()}:</strong> ${action}
            </div>
        `).join('');
        showOutput('followup_output', `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="margin-bottom: 15px;"><strong>Lead Category:</strong> ${data.category} | <strong>Score:</strong> ${data.score}/100</div>
                ${planSteps}
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 13px;">${data.note}</div>
            </div>
        `);
    } catch (e) {
        showOutput('followup_output', "Backend Error: Ensure server is running!");
    }
}
