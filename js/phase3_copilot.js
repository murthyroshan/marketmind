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
