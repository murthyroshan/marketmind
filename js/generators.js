/**
 * AI Logic Engines for SalesSpark AI
 * Connects to Python Backend (FastAPI) via REST API
 */

const API_BASE = "http://127.0.0.1:8000";

function showOutput(elementId, content, insight) {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.innerHTML = `
        ${content}
        <div class="ai-insight">
            🧠 <b>AI Insight:</b> ${insight}
        </div>
    `;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 1. Campaign Generator
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
        // Strict destructuring rule
        const { objective, theme, cta, outcome, ai_insight } = data;

        const content = `
            <strong>🎯 Objective:</strong> ${objective}<br>
            <strong>🎨 Theme:</strong> "${theme}"<br>
            <strong>📢 Key CTA:</strong> ${cta}<br>
            <strong>🏆 Outcome:</strong> ${outcome}
        `;

        showOutput('cG_output', content, ai_insight);
    } catch (e) {
        alert("Backend Error: Ensure server is running!");
    } finally {
        btn.innerText = originalText;
    }
}

// 2. Sales Pitch Generator
async function generatePitch() {
    const btn = document.querySelector('#sales button');
    btn.innerText = "Crafting...";

    try {
        const payload = {
            product: document.getElementById('sP_product').value || "Our Platform",
            client_type: document.getElementById('sP_client').value || "the prospect"
        };

        const res = await fetch(`${API_BASE}/pitch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        const { problem, value_prop, objection, closing, ai_insight } = data;

        const content = `
            <strong>⚠️ Problem:</strong> ${problem}<br>
            <strong>💎 Value Prop:</strong> ${value_prop}<br>
            <strong>🛡 Objection:</strong> ${objection}<br>
            <strong>🤝 Closing:</strong> ${closing}
        `;

        showOutput('sP_output', content, ai_insight);
    } catch (e) { console.error(e); } finally { btn.innerText = "Craft Pitch"; }
}

// 3. Lead Scoring
async function scoreLead() {
    const btn = document.querySelector('#analysis button') || event.target; // Fallback
    btn.innerText = "Analyzing...";

    try {
        const payload = {
            budget: parseInt(document.getElementById('lS_budget').value) || 0,
            interest: parseInt(document.getElementById('lS_interest').value) || 0,
            company_size: document.getElementById('lS_size').value
        };

        const res = await fetch(`${API_BASE}/leads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        const { score, category, recommendation, explanation } = data;

        const content = `
            <strong>📊 Score:</strong> ${score} / 100<br>
            <strong>🏷 Category:</strong> ${category}<br>
            <strong>🚀 Recommended Action:</strong> ${recommendation}
        `;

        // Use 'explanation' as the insight text
        showOutput('lS_output', content, explanation);
    } catch (e) { console.error(e); } finally { btn.innerText = "Analyze Lead"; }
}

// 4. Market Analysis
async function analyzeMarket() {
    try {
        const payload = { industry: document.getElementById('mA_industry').value || "Tech" };
        const res = await fetch(`${API_BASE}/market`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        const { trend, demand, competition, opportunity, ai_insight } = data;

        const content = `
            <strong>📈 Trend:</strong> ${trend}<br>
            <strong>🔥 Demand:</strong> ${demand}<br>
            <strong>⚔️ Competition:</strong> ${competition}<br>
            <strong>💡 Opportunity:</strong> ${opportunity}
        `;
        showOutput('mA_output', content, ai_insight);
    } catch (e) { console.error(e); }
}

// 5. Channel Content
async function generateContent() {
    try {
        const payload = {
            product: document.getElementById('cc_product').value || "Produce",
            platform: document.getElementById('cc_platform').value
        };
        const res = await fetch(`${API_BASE}/social`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        const { caption, hashtags, ai_insight } = data;

        const content = `
            <strong>📝 Capacitor:</strong><br>${caption}<br><br>
            <strong>🏷 Hashtags:</strong> ${hashtags}
        `;
        showOutput('cc_output', content, ai_insight);
    } catch (e) { console.error(e); }
}

// 6. Outreach
async function generateOutreach() {
    try {
        const payload = {
            product: document.getElementById('ao_product').value || "solution",
            customer_type: document.getElementById('ao_prospect').value || "Manager",
            goal: document.getElementById('ao_type').value
        };
        const res = await fetch(`${API_BASE}/email`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        const { subject, body, follow_up_tip } = data;

        const content = `
            <strong>📧 Subject:</strong> ${subject}<br>
            <strong>📄 Body:</strong><br>${body.replace(/\n/g, '<br>')}
        `;

        // Use follow_up_tip as insight
        showOutput('ao_output', content, follow_up_tip);
    } catch (e) { console.error(e); }
}

// 7. Campaign Performance Prediction
async function predictCampaign() {
    const btn = event.target;
    const originalText = btn.innerText;
    btn.innerText = "Predicting...";

    try {
        const payload = {
            platform: document.getElementById('pred_platform').value,
            goal: document.getElementById('pred_goal').value
        };

        const res = await fetch(`${API_BASE}/predict/campaign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        const riskColor = data.risk_level === 'Low' ? '#22c55e' : data.risk_level === 'Medium' ? '#f59e0b' : '#f87171';

        // Data source badge
        const isLive = data.data_source === "Live Database";
        const badgeIcon = isLive ? "🟢" : "🟡";
        const badgeColor = isLive ? "#22c55e" : "#f59e0b";
        const badgeText = data.data_source;

        // Professional card-based layout
        const content = `
            <div class="prediction-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7;">
                        🔬 Real-Time Prediction
                    </div>
                    <div style="background: ${badgeColor}15; border: 1px solid ${badgeColor}; color: ${badgeColor}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                        ${badgeIcon} ${badgeText}
                    </div>
                </div>

                <div class="metric-row">
                    <span>📈 Engagement Probability</span>
                    <span class="value green">${data.engagement_prob}%</span>
                </div>

                <div class="metric-row">
                    <span>💰 Conversion Probability</span>
                    <span class="value blue">${data.conversion_prob}%</span>
                </div>

                <div class="metric-row">
                    <span>⚠️ Risk Level</span>
                    <span class="value" style="color: ${riskColor}; font-size: 18px;">${data.risk_level}</span>
                </div>

                ${data.risk_level === 'High' ? `
                <div style="background: rgba(248,113,113,0.1); border-left: 3px solid #f87171; padding: 10px; margin: 10px 0; font-size: 13px; border-radius: 4px;">
                    ⚠️ High risk: Limited historical data on this platform
                </div>` : ''}

                <div class="ai-insight">
                    🧠 <b>AI Insight:</b>
                    <p style="margin: 8px 0 0 0; line-height: 1.5;">${data.explanation}</p>
                </div>

                <details class="data-used">
                    <summary style="cursor: pointer; font-weight: 600; margin-top: 8px;">📊 Metrics Used</summary>
                    <ul style="margin: 8px 0 0 0; padding-left: 20px; line-height: 1.8;">
                        <li>Total Leads: <b>${data.metrics_used.total_leads}</b></li>
                        <li>Avg Lead Score: <b>${data.metrics_used.avg_lead_score}/100</b></li>
                        <li>${payload.platform} Campaigns: <b>${data.metrics_used.platform_campaigns}</b></li>
                        <li>${payload.goal} Campaigns: <b>${data.metrics_used.goal_campaigns}</b></li>
                        <li>Hot Leads: <b>${data.metrics_used.hot_leads}</b></li>
                    </ul>
                </details>
            </div>
        `;

        // Display without using showOutput to avoid duplication
        const el = document.getElementById('pred_output');
        el.style.display = 'block';
        el.innerHTML = content;
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (e) {
        console.error(e);
        alert("Backend Error: Ensure server is running!");
    } finally {
        btn.innerText = originalText;
    }
}
// ==================== PHASE 3: SALES ACTION COPILOT ====================

// Deal Closure Assistant
async function getDealStrategy() {
    const leadId = document.getElementById('deal_lead_id').value;

    if (!leadId) {
        alert("Please enter a Lead ID");
        return;
    }

    try {
        const res = await fetch('http://127.0.0.1:8000/deal/assist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: parseInt(leadId) })
        });

        if (!res.ok) throw new Error("Failed to fetch strategy");

        const data = await res.json();

        if (data.error) {
            showOutput('deal_output', `❌ ${data.error}`);
            return;
        }

        // Color code urgency
        const urgencyColors = {
            "High": "#f87171",
            "Medium": "#f59e0b",
            "Low": "#22c55e"
        };
        const urgencyColor = urgencyColors[data.urgency_level] || "#94a3b8";

        const output = `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 15px; color: var(--primary);">
                    🎯 ${data.closing_strategy}
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>💰 Discount Range:</strong> <span style="color: var(--success);">${data.discount_range}</span>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>🎯 Objection Focus:</strong> ${data.objection_focus}
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>⚡ Urgency:</strong> <span style="color: ${urgencyColor}; font-weight: 700;">${data.urgency_level}</span>
                </div>
                
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 14px;">
                    <strong>💡 Reasoning:</strong> ${data.explanation}
                </div>
            </div>
        `;

        showOutput('deal_output', output);
    } catch (e) {
        console.error(e);
        showOutput('deal_output', "❌  Backend Error: Ensure server is running!");
    }
}

// Follow-up Planner
async function getFollowupPlan() {
    const leadId = document.getElementById('followup_lead_id').value;

    if (!leadId) {
        alert("Please enter a Lead ID");
        return;
    }

    try {
        const res = await fetch('http://127.0.0.1:8000/followup/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: parseInt(leadId) })
        });

        if (!res.ok) throw new Error("Failed to generate plan");

        const data = await res.json();

        if (data.error) {
            showOutput('followup_output', `❌ ${data.error}`);
            return;
        }

        const planSteps = Object.entries(data.plan).map(([day, action]) => {
            return `<div style="margin-bottom: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <strong style="color: var(--primary);">${day.toUpperCase()}:</strong> ${action}
            </div>`;
        }).join('');

        const output = `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="margin-bottom: 15px;">
                    <strong>Lead Category:</strong> <span style="color: var(--primary); font-weight: 700;">${data.category}</span> | 
                    <strong>Score:</strong> ${data.score}/100
                </div>
                
                ${planSteps}
                
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 13px;">
                    💡 ${data.note}
                </div>
            </div>
        `;

        showOutput('followup_output', output);
    } catch (e) {
        console.error(e);
        showOutput('followup_output', "❌ Backend Error: Ensure server is running!");
    }
}
