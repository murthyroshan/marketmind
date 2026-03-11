/**
 * copilot_page.js
 * ─────────────────────────────────────────────────────────────────────────────────
 * Powers every dynamic section of the SalesSparkAI Copilot dashboard page.
 *
 * Sections managed:
 *  1. KPI pipeline cards      ← /dashboard
 *  2. AI Insights panel       ← derived from /dashboard + /actions/next
 *  3. Next Best Actions list  ← /actions/next
 *  4. Sales Momentum block    ← /trends/sales
 *  5. Active Alerts           ← /alerts
 */

const API = 'http://127.0.0.1:8000';

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await Promise.allSettled([
        loadKPIs(),
        loadNextActions(),
        loadSalesTrends(),
        loadAlerts(),
    ]);
    // Insights depend on actions — populate after both resolve
    // (loadNextActions sets window._copilotActions)
    buildInsights();
});

// ── 1. KPI Cards ──────────────────────────────────────────────────────────────
async function loadKPIs() {
    try {
        const res = await fetch(`${API}/dashboard`);
        const data = await res.json();
        const m = data.metrics || {};

        setText('kpi-total', m.total_leads ?? '–');
        setText('kpi-hot', m.hot_leads ?? '–');
        setText('kpi-avg', m.avg_lead_score ?? '–');

        // Warm / Cold aren't in /dashboard — fetch from /leads and count client-side
        try {
            const lr = await fetch(`${API}/leads`);
            const ldata = await lr.json();
            const leads = ldata.leads || [];

            const counts = { Hot: 0, Warm: 0, Cold: 0 };
            leads.forEach(l => {
                if (counts[l.category] !== undefined) counts[l.category]++;
            });

            setText('kpi-hot', counts.Hot);
            setText('kpi-warm', counts.Warm);
            setText('kpi-cold', counts.Cold);
        } catch (e) {
            console.warn('[Copilot] Lead count failed:', e);
            setText('kpi-warm', '–');
            setText('kpi-cold', '–');
        }

        // Pipeline health badge
        const health = data.metrics?.lead_quality_trend ?? '';
        const healthEl = document.getElementById('kpi-health');
        if (healthEl && health) {
            healthEl.textContent = health;
            if (health === 'Improving') {
                healthEl.style.color = '#34d399';
                healthEl.style.background = 'rgba(52,211,153,0.12)';
            } else if (health === 'Stable') {
                healthEl.style.color = '#f59e0b';
                healthEl.style.background = 'rgba(245,158,11,0.12)';
            }
        }

        // Store for insights
        window._copilotMetrics = m;

    } catch (e) {
        console.warn('[Copilot] KPI load failed:', e);
        ['kpi-total', 'kpi-hot', 'kpi-warm', 'kpi-cold', 'kpi-avg'].forEach(id =>
            setText(id, '–')
        );
    }
}


// ── 2. AI Insights Panel ──────────────────────────────────────────────────────
function buildInsights() {
    const container = document.getElementById('insights-panel');
    if (!container) return;

    const m = window._copilotMetrics || {};
    const actions = window._copilotActions || [];

    const insights = [];

    // --- Lead quality insight ---
    const hot = m.hot_leads ?? 0;
    const tot = m.total_leads ?? 0;
    const avg = m.avg_lead_score ?? 0;

    if (hot >= 3) {
        insights.push({
            icon: '🔥',
            html: `<strong>${hot} hot leads</strong> are ready to close. Schedule calls within 48 hours to maximize conversion.`,
        });
    } else if (hot === 0) {
        insights.push({
            icon: '⚠️',
            html: `<strong>No hot leads</strong> in your pipeline. Consider launching a campaign to generate high-intent prospects.`,
        });
    } else {
        insights.push({
            icon: '🌡️',
            html: `You have <strong>${hot} hot lead${hot > 1 ? 's' : ''}</strong>. Prioritize outreach with a personalized pitch.`,
        });
    }

    // --- Avg score insight ---
    if (avg > 0) {
        if (avg >= 65) {
            insights.push({
                icon: '✅',
                html: `Pipeline quality is <strong>strong</strong> (avg ${avg}/100). Focus on closing hot leads and nurturing warm ones.`,
            });
        } else if (avg >= 45) {
            insights.push({
                icon: '📈',
                html: `Avg lead score is <strong>${avg}/100</strong>. Use the Email Generator to nurture warm leads toward conversion.`,
            });
        } else {
            insights.push({
                icon: '📉',
                html: `Avg lead score is <strong>${avg}/100</strong> — below target. Run a new lead scoring session using⚖️ Lead Scoring.`,
            });
        }
    }

    // --- Top action insight ---
    if (actions.length > 0) {
        const top = actions[0];
        insights.push({
            icon: '🎯',
            html: `Top priority: <strong>Lead #${top.lead_id}</strong> (${top.category}, ${top.score}/100). ${top.action}`,
        });
    }

    // --- Campaign suggestion ---
    insights.push({
        icon: '🚀',
        html: `Try the <strong>Campaign Generator</strong> to launch a targeted outreach on LinkedIn or Email for your warm leads.`,
    });

    // --- Market suggestion ---
    insights.push({
        icon: '📊',
        html: `Use <strong>Market Intelligence</strong> to identify high-demand industries and align your pipeline strategy.`,
    });

    // Render
    container.innerHTML = insights.map(ins => `
        <div class="insight-item">
            <span class="insight-icon">${ins.icon}</span>
            <span class="insight-text">${ins.html}</span>
        </div>
    `).join('');
}


// ── 3. Next Best Actions ───────────────────────────────────────────────────────
async function loadNextActions() {
    const container = document.getElementById('next-actions-container');
    try {
        const res = await fetch(`${API}/actions/next`);
        const data = await res.json();

        if (!data.actions || data.actions.length === 0) {
            container.innerHTML = `
                <div style="padding:28px;text-align:center;color:var(--text-muted);font-size:14px;">
                    📭 ${data.message || 'No actions available. Add leads to see prioritized recommendations.'}
                </div>`;
            return;
        }

        // Store for insights panel — normalize field names
        window._copilotActions = data.actions.map(item => ({
            lead_id: item.lead_id,
            category: item.category ?? item.priority ?? 'Warm',
            score: item.score ?? 0,
            action: item.action ?? '',
            reason: item.reason || '',
        }));

        const COLOR = { Hot: '#f87171', Warm: '#f59e0b', Cold: '#94a3b8' };

        container.innerHTML = window._copilotActions.map((item, i) => {
            const cat = item.category;
            const c = COLOR[cat] || '#60a5fa';
            const rank = i + 1;
            return `
                <div class="action-row" style="--action-color:${c};">
                    <div class="action-rank">${rank}</div>
                    <div class="action-info">
                        <div class="action-lead">
                            Lead #${item.lead_id}
                            <span class="category-badge" style="background:${c}18;color:${c};margin-left:6px;">
                                ${cat} · ${item.score}/100
                            </span>
                        </div>
                        <div class="action-text">${item.action}</div>
                        ${item.reason ? `<div class="action-reason">💡 ${item.reason}</div>` : ''}
                    </div>
                </div>`;
        }).join('');

    } catch (e) {
        console.warn('[Copilot] Next actions failed:', e);
        container.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">Unable to load actions. Is the server running?</div>`;
    }
}


// ── 4. Sales Trends (Momentum) ────────────────────────────────────────────────
async function loadSalesTrends() {
    try {
        const res = await fetch(`${API}/trends/sales`);
        const data = await res.json();

        const TREND_COLOR = {
            improving: '#22c55e',
            declining: '#f87171',
            stable: '#f59e0b',
            insufficient: '#94a3b8',
        };
        const color = TREND_COLOR[data.trend] || '#94a3b8';

        const badge = document.getElementById('trend-badge');
        const dir = document.getElementById('trend-direction');
        const risk = document.getElementById('risk-container');
        const opp = document.getElementById('opportunity-container');

        if (badge) badge.innerHTML = `<span style="color:${color};">${data.trend_direction ?? data.trend}</span>`;
        if (dir && data.trend_reason) {
            dir.innerHTML = `<em style="font-size:13px;">${data.trend_reason}</em>`;
        }

        // Risk flags
        if (risk) {
            if (data.risk_flags?.length > 0) {
                const rows = data.risk_flags.map(r =>
                    typeof r === 'string'
                        ? `<li>${r}</li>`
                        : `<li><strong>${r.alert}</strong><br><em style="font-size:12px;color:var(--text-muted);">${r.reason}</em></li>`
                ).join('');
                risk.innerHTML = `
                    <div class="flag-block risk">
                        <strong style="color:#f87171;font-size:13px;">⚠️ Risk Alerts</strong>
                        <ul>${rows}</ul>
                    </div>`;
            } else {
                risk.innerHTML = `
                    <div class="flag-block clear">
                        ✅ <strong style="color:#22c55e;">No active risks detected</strong>
                    </div>`;
            }
        }

        // Opportunity flags
        if (opp && data.opportunity_flags?.length > 0) {
            const rows = data.opportunity_flags.map(o =>
                typeof o === 'string'
                    ? `<li>${o}</li>`
                    : `<li><strong>${o.alert}</strong><br><em style="font-size:12px;color:var(--text-muted);">${o.reason}</em></li>`
            ).join('');
            opp.innerHTML = `
                <div class="flag-block opportunity">
                    <strong style="color:#22c55e;font-size:13px;">🎯 Opportunities</strong>
                    <ul>${rows}</ul>
                </div>`;
        }

    } catch (e) {
        console.warn('[Copilot] Trends failed:', e);
        const badge = document.getElementById('trend-badge');
        if (badge) badge.innerHTML = '<span style="color:var(--text-muted);">Unavailable</span>';
    }
}


// ── 5. Active Alerts ──────────────────────────────────────────────────────────
async function loadAlerts() {
    try {
        const res = await fetch(`${API}/alerts`);
        const data = await res.json();

        const wrapper = document.getElementById('alerts-container');
        const inner = document.getElementById('alerts-inner');

        if (!data.alerts?.length) {
            if (wrapper) wrapper.style.display = 'none';
            return;
        }

        if (wrapper) wrapper.style.display = 'block';
        if (!inner) return;

        inner.innerHTML = data.alerts.map(a => {
            const c = a.level === 'warning' ? '#f87171' : '#60a5fa';
            return `
                <div class="alert-item" style="border:1px solid ${c};background:${c}0f;margin-bottom:10px;">
                    <h4 style="color:${c};margin:0 0 4px;font-size:14px;">${a.message}</h4>
                    <p style="font-size:13px;color:var(--text-muted);margin:0;">${a.reason}</p>
                </div>`;
        }).join('');

    } catch (e) {
        console.warn('[Copilot] Alerts failed:', e);
    }
}




// ── Dashboard Refresh ─────────────────────────────────────────────────────────
async function refreshDashboard() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
    }
    await Promise.allSettled([loadKPIs(), loadNextActions(), loadSalesTrends(), loadAlerts()]);
    buildInsights();
    if (btn) {
        btn.style.opacity = '';
        btn.style.pointerEvents = '';
    }
}


// ── Utility ───────────────────────────────────────────────────────────────────
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
