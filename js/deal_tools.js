// Global variable for selected lead
let selectedLeadId = null;

// Load leads on page load
document.addEventListener('DOMContentLoaded', () => {
    loadLeadsDropdown();
});

// Load leads into dropdown
async function loadLeadsDropdown() {
    try {
        const res = await fetch('http://127.0.0.1:8000/leads');
        const data = await res.json();

        const dropdown = document.getElementById('lead-selector');
        const status = document.getElementById('lead-selector-status');

        if (!data.leads || data.leads.length === 0) {
            status.innerHTML = '⚠️ No leads found. Generate leads first.';
            status.style.color = 'var(--warning)';
            return;
        }

        // Populate dropdown
        data.leads.forEach(lead => {
            const option = document.createElement('option');
            option.value = lead.id;
            option.textContent = `Lead #${lead.id} — ${lead.category} — Score ${lead.score}`;
            dropdown.appendChild(option);
        });

        status.innerHTML = `✅ ${data.leads.length} leads available`;
        status.style.color = 'var(--success)';

        // Enable selection
        dropdown.addEventListener('change', (e) => {
            selectedLeadId = e.target.value ? parseInt(e.target.value) : null;

            const dealBtn = document.getElementById('deal-btn');
            const followupBtn = document.getElementById('followup-btn');

            if (selectedLeadId) {
                dealBtn.disabled = false;
                followupBtn.disabled = false;
                status.innerHTML = `✅ Lead #${selectedLeadId} selected`;
                status.style.color = 'var(--success)';
            } else {
                dealBtn.disabled = true;
                followupBtn.disabled = true;
                status.innerHTML = '⚠️ Please select a lead';
                status.style.color = 'var(--warning)';
            }
        });

    } catch (e) {
        console.error('Failed to load leads:', e);
        document.getElementById('lead-selector-status').innerHTML = '❌ Failed to load leads. Ensure backend is running.';
        document.getElementById('lead-selector-status').style.color = 'var(--error)';
    }
}

// Deal Closure Assistant
async function getDealStrategy() {
    if (!selectedLeadId) {
        alert("⚠️ Please select a lead first");
        return;
    }

    const btn = document.getElementById('deal-btn');
    const originalText = btn.innerText;
    btn.innerText = "Analyzing...";

    try {
        const res = await fetch('http://127.0.0.1:8000/deal/assist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: selectedLeadId })
        });

        const data = await res.json();

        if (data.error) {
            showOutput('deal_output', `❌ ${data.error}`);
            btn.innerText = originalText;
            return;
        }

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
        btn.innerText = originalText;
    } catch (e) {
        console.error(e);
        showOutput('deal_output', "❌ Backend Error: Ensure server is running!");
        btn.innerText = originalText;
    }
}

// Follow-up Planner
async function getFollowupPlan() {
    if (!selectedLeadId) {
        alert("⚠️ Please select a lead first");
        return;
    }

    const btn = document.getElementById('followup-btn');
    const originalText = btn.innerText;
    btn.innerText = "Generating...";

    try {
        const res = await fetch('http://127.0.0.1:8000/followup/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: selectedLeadId })
        });

        const data = await res.json();

        if (data.error) {
            showOutput('followup_output', `❌ ${data.error}`);
            btn.innerText = originalText;
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
        btn.innerText = originalText;
    } catch (e) {
        console.error(e);
        showOutput('followup_output', "❌ Backend Error: Ensure server is running!");
        btn.innerText = originalText;
    }
}

// Helper function
function showOutput(elementId, htmlContent) {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.innerHTML = htmlContent;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
