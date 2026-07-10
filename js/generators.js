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
        if (!res.ok) throw new Error("HTTP " + res.status);
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
        showOutput('mA_output', "<b style='color:red'>Backend Error: Ensure server is running!</b>");
    }
}

async function generateContent() {
    const product = document.getElementById("contentProduct").value;
    const platform = document.getElementById("contentPlatform").value;

    const output = document.getElementById("contentOutput");
    try {
        const res = await fetch(`${API_BASE}/social`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product, platform })
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();

        output.style.display = "block";
        output.innerHTML = `
            <h4>Generated Content</h4>
            <p><b>Tone:</b> ${data.tone}</p>
            <p><b>Caption:</b><br>${data.caption}</p>
            <p><b>Hashtags:</b> ${data.hashtags}</p>
            <p><i>${data.ai_insight}</i></p>
        `;
    } catch (e) {
        output.style.display = "block";
        output.innerHTML = "<b style='color:red'>Backend Error: Ensure server is running!</b>";
    }
}

async function generateEmail() {
    const recipient = document.getElementById("emailRecipient").value;
    const context = document.getElementById("emailContext").value;
    const product = document.getElementById("emailProduct").value;

    const output = document.getElementById("emailOutput");
    try {
        const res = await fetch(`${API_BASE}/email`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ recipient, context, product })
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();

        output.style.display = 'block';
        output.innerHTML = `
            <b>Subject:</b> ${data.subject}<br><br>
            <pre>${data.body}</pre><br>
            <i>${data.follow_up_tip}</i>
        `;
    } catch (e) {
        output.style.display = 'block';
        output.innerHTML = "<b style='color:red'>Backend Error: Ensure server is running!</b>";
    }
}

// NOTE: getDealStrategy() and getFollowupPlan() live in deal_tools.js, which
// leads.html loads after this file. The duplicate definitions that used to be
// here were dead (always overridden) and read element ids that don't exist on
// this page, so they were removed to avoid load-order fragility.
