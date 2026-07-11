let selectedLeadId = null;

// leads.html already fetches GET /leads to build the table, so it hands the
// same rows straight to us instead of us fetching them a second time.
function populateLeadsDropdown(leads) {
    try {
        const dropdown = document.getElementById('lead-selector');
        const status = document.getElementById('lead-selector-status');
        if (!dropdown || !status) return;

        if (!leads || !leads.length) {
            status.innerHTML = 'No leads found. Generate leads first.';
            status.style.color = 'var(--warning)';
            return;
        }

        leads.forEach(lead => {
            const option = document.createElement('option');
            option.value = lead.id;
            option.textContent = `${lead.company || `Lead #${lead.id}`} - ${lead.category} - Score ${lead.score} - ${lead.deal_stage || 'Prospecting'}`;
            dropdown.appendChild(option);
        });

        status.innerHTML = `${leads.length} leads available`;
        status.style.color = 'var(--success)';

        dropdown.addEventListener('change', (e) => {
            selectedLeadId = e.target.value ? parseInt(e.target.value, 10) : null;
            const dealBtn = document.getElementById('deal-btn');
            const followupBtn = document.getElementById('followup-btn');

            if (selectedLeadId) {
                dealBtn.disabled = false;
                followupBtn.disabled = false;
                status.innerHTML = `Lead #${selectedLeadId} selected`;
                status.style.color = 'var(--success)';
            } else {
                dealBtn.disabled = true;
                followupBtn.disabled = true;
                status.innerHTML = 'Please select a lead';
                status.style.color = 'var(--warning)';
            }
        });
    } catch (e) {
        const status = document.getElementById('lead-selector-status');
        if (status) {
            status.innerHTML = 'Failed to load leads. Ensure backend is running.';
            status.style.color = 'var(--error)';
        }
    }
}

async function getDealStrategy() {
    if (!selectedLeadId) {
        alert('Please select a lead first');
        return;
    }

    const btn = document.getElementById('deal-btn');
    const originalText = btn.innerText;
    btn.innerText = 'Analyzing...';

    try {
        const res = await fetch('http://127.0.0.1:8000/deal/assist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: selectedLeadId })
        });
        const data = await res.json();

        if (data.error) {
            showOutput('deal_output', escapeHtml(data.error));
            return;
        }

        const output = `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 18px; font-weight: 700; margin-bottom: 15px; color: var(--primary);">${escapeHtml(data.closing_strategy)}</div>
                <div style="margin-bottom: 12px;"><strong>Negotiation Advice:</strong> ${escapeHtml(data.negotiation_advice || data.objection_focus)}</div>
                <div style="margin-bottom: 12px;"><strong>Recommended Next Step:</strong> ${escapeHtml(data.recommended_next_step || data.explanation)}</div>
                <div style="margin-bottom: 12px;"><strong>Urgency:</strong> ${escapeHtml(data.urgency_level)}</div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 14px;"><strong>Reasoning:</strong> ${escapeHtml(data.explanation)}</div>
            </div>
        `;

        showOutput('deal_output', output);
    } catch (e) {
        showOutput('deal_output', 'Backend Error: Ensure server is running!');
    } finally {
        btn.innerText = originalText;
    }
}

async function getFollowupPlan() {
    if (!selectedLeadId) {
        alert('Please select a lead first');
        return;
    }

    const btn = document.getElementById('followup-btn');
    const originalText = btn.innerText;
    btn.innerText = 'Generating...';

    try {
        const res = await fetch('http://127.0.0.1:8000/followup/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lead_id: selectedLeadId })
        });
        const data = await res.json();

        if (data.error) {
            showOutput('followup_output', escapeHtml(data.error));
            return;
        }

        if (!data.plan || typeof data.plan !== 'object') {
            showOutput('followup_output', 'No follow-up plan was returned. Please try again.');
            return;
        }

        const planSteps = Object.entries(data.plan).map(([day, action]) => `
            <div style="margin-bottom: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <strong style="color: var(--primary);">${escapeHtml(day.toUpperCase())}:</strong> ${escapeHtml(action)}
            </div>
        `).join('');

        showOutput('followup_output', `
            <div style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="margin-bottom: 15px;"><strong>Lead Category:</strong> ${escapeHtml(data.category)} | <strong>Score:</strong> ${escapeHtml(data.score)}/100</div>
                ${planSteps}
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); color: var(--text-muted); font-size: 13px;">${escapeHtml(data.note)}</div>
            </div>
        `);
    } catch (e) {
        showOutput('followup_output', 'Backend Error: Ensure server is running!');
    } finally {
        btn.innerText = originalText;
    }
}

function showOutput(elementId, htmlContent) {
    const el = document.getElementById(elementId);
    el.style.display = 'block';
    el.innerHTML = htmlContent;
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
