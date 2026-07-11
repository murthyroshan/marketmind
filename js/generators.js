// API_BASE and escapeHtml come from js/app.js, which every page loads first.

// Everything the backend returns here is derived from what the user typed (the
// AI fallbacks interpolate the industry/product/company straight into their
// strings), so every value must be escaped before it reaches innerHTML.
const esc = (v) => escapeHtml(v == null ? '' : v);

function showOutput(elementId, content, insight = "") {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.innerHTML = `
        ${content}
        ${insight ? `<div class="ai-insight"><b>AI Insight:</b> ${esc(insight)}</div>` : ''}
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
            <strong>Objective:</strong> ${esc(data.objective)}<br>
            <strong>Campaign Theme:</strong> ${esc(data.theme)}<br>
            <strong>Marketing Strategy:</strong> ${esc(data.marketing_strategy)}<br>
            <strong>Messaging Approach:</strong> ${esc(data.messaging_approach)}<br>
            <strong>CTA:</strong> ${esc(data.cta)}<br>
            <strong>Expected Outcome:</strong> ${esc(data.outcome)}
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
            <b>Opening Hook:</b> ${esc(data.opening_hook)}<br>
            <b>Problem Framing:</b> ${esc(data.problem_framing)}<br>
            <b>Product Positioning:</b> ${esc(data.product_positioning)}<br>
            <b>Objection Handling:</b> ${esc(data.objection_handling)}<br>
            <b>Closing Statement:</b> ${esc(data.closing_statement)}
        `;
    } catch (e) {
        document.getElementById("pitchOutput").style.display = 'block';
        document.getElementById("pitchOutput").innerHTML = `<b style='color:red'>Error: ${esc(e.message)}</b>`;
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
            <b>Score:</b> ${esc(data.score)}/100<br>
            <b>Category:</b> ${esc(data.category)}<br>
            <b>Recommendation:</b> ${esc(data.recommendation)}<br>
            <b>Explanation:</b> ${esc(data.explanation)}
        `;
    } catch (e) {
        document.getElementById("leadOutput").style.display = 'block';
        document.getElementById("leadOutput").innerHTML = `<b style='color:red'>Error: ${esc(e.message)}</b>`;
    }
}

async function analyzeMarket() {
    try {
        const payload = { industry: document.getElementById('mA_industry').value || "saas" };
        const res = await fetch(`${API_BASE}/market/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        const content = `
            <strong>Demand Insight:</strong> ${esc(data.market_trend_summary)}<br>
            <strong>Demand Level:</strong> ${esc(data.demand_level)}<br>
            <strong>Competition Overview:</strong> ${esc(data.competition_overview)}<br>
            <strong>Opportunity Summary:</strong> ${esc(data.opportunity_insights)}
        `;
        showOutput('mA_output', content, data.insight);
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
            <p><b>Tone:</b> ${esc(data.tone)}</p>
            <p><b>Caption:</b><br>${esc(data.caption)}</p>
            <p><b>Hashtags:</b> ${esc(data.hashtags)}</p>
            <p><i>${esc(data.ai_insight)}</i></p>
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
            <b>Subject:</b> ${esc(data.subject)}<br><br>
            <pre>${esc(data.body)}</pre><br>
            <i>${esc(data.follow_up_tip)}</i>
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
