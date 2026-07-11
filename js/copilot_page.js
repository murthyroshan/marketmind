const API = 'http://127.0.0.1:8000';

// escapeHtml() comes from js/app.js, which sales_copilot.html loads first.

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

        // countUp() lives in app.js, which this page loads first.
        countUp(document.getElementById('kpi-total'), m.total_leads ?? 0);
        countUp(document.getElementById('kpi-hot'), m.hot_leads ?? 0);
        countUp(document.getElementById('kpi-warm'), m.warm_leads ?? 0);
        countUp(document.getElementById('kpi-cold'), m.cold_leads ?? 0);
        countUp(document.getElementById('kpi-avg'), m.avg_lead_score ?? 0);

        const healthEl = document.getElementById('kpi-health');
        if (healthEl) {
            const trend = m.lead_quality_trend || '';
            healthEl.textContent = trend.toUpperCase();
            const tone = trend === 'Improving' ? 'var(--up)'
                : trend === 'Needs Attention' ? 'var(--hot)'
                    : 'var(--warm)';
            healthEl.style.color = tone;
            healthEl.style.borderColor = tone;
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
                <span class="insight-text">${escapeHtml(text)}</span>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="insight-item"><span class="insight-icon">AI</span><span class="insight-text">Insights are temporarily unavailable.</span></div>`;
    }
}

async function loadNextActions() {
    const container = document.getElementById('next-actions-container');
    if (!container) return;
    try {
        const res = await fetch(`${API}/actions/next`);
        const data = await res.json();

        if (!data.actions || data.actions.length === 0) {
            container.innerHTML = `<div class="panel-empty">${data.message || 'No actions available.'}</div>`;
            return;
        }

        const COLOR = { Hot: 'var(--hot)', Warm: 'var(--warm)', Cold: 'var(--cold)' };
        container.innerHTML = data.actions.map((item, i) => {
            const c = COLOR[item.category] || 'var(--cold)';
            return `
                <div class="action-row" style="--action-color:${c};">
                    <div class="action-rank">${i + 1}</div>
                    <div class="action-info">
                        <div class="action-lead">
                            ${escapeHtml(item.company || `Lead #${item.lead_id}`)}
                            <span class="category-badge" style="color:${c};">${escapeHtml(item.category)} • ${escapeHtml(item.score)}/100</span>
                        </div>
                        <div class="action-text">${escapeHtml(item.action)}</div>
                        <div class="action-reason">${escapeHtml(item.reason)}</div>
                    </div>
                </div>`;
        }).join('');
    } catch (e) {
        container.innerHTML = `<div class="panel-empty">Unable to load actions.</div>`;
    }
}

async function loadSalesTrends() {
    try {
        const res = await fetch(`${API}/trends/sales`);
        const data = await res.json();
        const TREND_COLOR = { improving: 'var(--up)', declining: 'var(--hot)', stable: 'var(--warm)', insufficient: 'var(--cold)' };
        const color = TREND_COLOR[data.trend] || 'var(--cold)';

        const badge = document.getElementById('trend-badge');
        const dir = document.getElementById('trend-direction');
        const risk = document.getElementById('risk-container');
        const opp = document.getElementById('opportunity-container');

        if (badge) badge.innerHTML = `<span style="color:${color};">${escapeHtml(data.trend_direction ?? data.trend)}</span>`;
        if (dir && data.trend_reason) dir.innerHTML = `<em style="font-size:13px;">${escapeHtml(data.trend_reason)}</em>`;

        if (risk) {
            risk.innerHTML = data.risk_flags?.length
                ? `<div class="flag-block risk"><strong style="color:var(--hot);font-size:12px;">Risk Alerts</strong><ul>${data.risk_flags.map(r => `<li><strong>${escapeHtml(r.alert)}</strong><br><em style="font-size:12px;color:var(--text-muted);">${escapeHtml(r.reason)}</em></li>`).join('')}</ul></div>`
                : `<div class="flag-block clear">No active risks detected</div>`;
        }

        if (opp) {
            opp.innerHTML = data.opportunity_flags?.length
                ? `<div class="flag-block opportunity"><strong style="color:var(--up);font-size:12px;">Opportunities</strong><ul>${data.opportunity_flags.map(o => `<li><strong>${escapeHtml(o.alert)}</strong><br><em style="font-size:12px;color:var(--text-muted);">${escapeHtml(o.reason)}</em></li>`).join('')}</ul></div>`
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
            const c = a.level === 'warning' ? 'var(--hot)' : 'var(--warm)';
            return `<div class="alert-item" style="border:1px solid ${c};background:${c}0f;margin-bottom:10px;"><h4 style="color:${c};margin:0 0 4px;font-size:14px;">${escapeHtml(a.message)}</h4><p style="font-size:13px;color:var(--text-muted);margin:0;">${escapeHtml(a.reason)}</p></div>`;
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
