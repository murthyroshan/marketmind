const API = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', async () => {
    await Promise.allSettled([
        loadKPIs(),
        loadNextActions(),
        loadSalesTrends(),
        loadAlerts(),
        loadInsights(),
    ]);
});

async function loadKPIs() {
    try {
        const res = await fetch(`${API}/dashboard`);
        const data = await res.json();
        const m = data.metrics || {};

        setText('kpi-total', m.total_leads ?? '-');
        setText('kpi-hot', m.hot_leads ?? '-');
        setText('kpi-warm', m.warm_leads ?? '-');
        setText('kpi-cold', m.cold_leads ?? '-');
        setText('kpi-avg', m.avg_lead_score ?? '-');

        const healthEl = document.getElementById('kpi-health');
        if (healthEl) {
            healthEl.textContent = m.lead_quality_trend || '';
            if (m.lead_quality_trend === 'Improving') {
                healthEl.style.color = '#34d399';
                healthEl.style.background = 'rgba(52,211,153,0.12)';
            } else if (m.lead_quality_trend === 'Needs Attention') {
                healthEl.style.color = '#f87171';
                healthEl.style.background = 'rgba(248,113,113,0.12)';
            } else {
                healthEl.style.color = '#f59e0b';
                healthEl.style.background = 'rgba(245,158,11,0.12)';
            }
        }
    } catch (e) {
        ['kpi-total', 'kpi-hot', 'kpi-warm', 'kpi-cold', 'kpi-avg'].forEach(id => setText(id, '-'));
    }
}

async function loadInsights() {
    const container = document.getElementById('insights-panel');
    if (!container) return;

    try {
        const res = await fetch(`${API}/copilot/insights`);
        const data = await res.json();
        const items = [data.summary, ...(data.insights || [])].filter(Boolean);
        container.innerHTML = items.map(text => `
            <div class="insight-item">
                <span class="insight-icon">AI</span>
                <span class="insight-text">${text}</span>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="insight-item"><span class="insight-icon">AI</span><span class="insight-text">Insights are temporarily unavailable.</span></div>`;
    }
}

async function loadNextActions() {
    const container = document.getElementById('next-actions-container');
    try {
        const res = await fetch(`${API}/actions/next`);
        const data = await res.json();

        if (!data.actions || data.actions.length === 0) {
            container.innerHTML = `<div style="padding:28px;text-align:center;color:var(--text-muted);font-size:14px;">${data.message || 'No actions available.'}</div>`;
            return;
        }

        const COLOR = { Hot: '#f87171', Warm: '#f59e0b', Cold: '#94a3b8' };
        container.innerHTML = data.actions.map((item, i) => {
            const c = COLOR[item.category] || '#60a5fa';
            return `
                <div class="action-row" style="--action-color:${c};">
                    <div class="action-rank">${i + 1}</div>
                    <div class="action-info">
                        <div class="action-lead">
                            ${item.company || `Lead #${item.lead_id}`}
                            <span class="category-badge" style="background:${c}18;color:${c};margin-left:6px;">${item.category} · ${item.score}/100</span>
                        </div>
                        <div class="action-text">${item.action}</div>
                        <div class="action-reason">${item.reason}</div>
                    </div>
                </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">Unable to load actions.</div>`;
    }
}

async function loadSalesTrends() {
    try {
        const res = await fetch(`${API}/trends/sales`);
        const data = await res.json();
        const TREND_COLOR = { improving: '#22c55e', declining: '#f87171', stable: '#f59e0b', insufficient: '#94a3b8' };
        const color = TREND_COLOR[data.trend] || '#94a3b8';

        const badge = document.getElementById('trend-badge');
        const dir = document.getElementById('trend-direction');
        const risk = document.getElementById('risk-container');
        const opp = document.getElementById('opportunity-container');

        if (badge) badge.innerHTML = `<span style="color:${color};">${data.trend_direction ?? data.trend}</span>`;
        if (dir && data.trend_reason) dir.innerHTML = `<em style="font-size:13px;">${data.trend_reason}</em>`;

        if (risk) {
            risk.innerHTML = data.risk_flags?.length
                ? `<div class="flag-block risk"><strong style="color:#f87171;font-size:13px;">Risk Alerts</strong><ul>${data.risk_flags.map(r => `<li><strong>${r.alert}</strong><br><em style="font-size:12px;color:var(--text-muted);">${r.reason}</em></li>`).join('')}</ul></div>`
                : `<div class="flag-block clear">No active risks detected</div>`;
        }

        if (opp) {
            opp.innerHTML = data.opportunity_flags?.length
                ? `<div class="flag-block opportunity"><strong style="color:#22c55e;font-size:13px;">Opportunities</strong><ul>${data.opportunity_flags.map(o => `<li><strong>${o.alert}</strong><br><em style="font-size:12px;color:var(--text-muted);">${o.reason}</em></li>`).join('')}</ul></div>`
                : '';
        }
    } catch (e) {
        const badge = document.getElementById('trend-badge');
        if (badge) badge.innerHTML = '<span style="color:var(--text-muted);">Unavailable</span>';
    }
}

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
            return `<div class="alert-item" style="border:1px solid ${c};background:${c}0f;margin-bottom:10px;"><h4 style="color:${c};margin:0 0 4px;font-size:14px;">${a.message}</h4><p style="font-size:13px;color:var(--text-muted);margin:0;">${a.reason}</p></div>`;
        }).join('');
    } catch (e) {
        console.warn('[Copilot] Alerts failed:', e);
    }
}

async function refreshDashboard() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
    }
    await Promise.allSettled([loadKPIs(), loadNextActions(), loadSalesTrends(), loadAlerts(), loadInsights()]);
    if (btn) {
        btn.style.opacity = '';
        btn.style.pointerEvents = '';
    }
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
