// EXTRACTED LOGIC FOR SALES COPILOT PAGE ONLY

document.addEventListener('DOMContentLoaded', async () => {
    await loadNextActions();
    await loadSalesTrends();
    await loadAlerts();
});

async function loadNextActions() {
    try {
        const res = await fetch('http://127.0.0.1:8000/actions/next');
        const data = await res.json();

        const container = document.getElementById('next-actions-container');

        if (!data.actions || data.actions.length === 0) {
            container.innerHTML = `<div class="card" style="text-align: center; padding: 40px; color: var(--text-muted);">
                📭 ${data.message || 'No actions available. Add leads to see prioritized recommendations.'}
            </div>`;
            return;
        }

        const categoryColors = {
            "Hot": "#f87171",
            "Warm": "#f59e0b",
            "Cold": "#94a3b8"
        };

        const actionsHTML = data.actions.map((item, index) => {
            const color = categoryColors[item.category] || "#60a5fa";
            const rank = index + 1;

            return `
                <div class="card" style="margin-bottom: 15px; border-left: 4px solid ${color}; position: relative;">
                    <div style="position: absolute; top: 10px; right: 10px; background: ${color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">
                        ${rank}
                    </div>
                    <div style="padding-right: 50px;">
                        <div style="font-weight: 700; margin-bottom: 8px;">Lead #${item.lead_id} <span style="background: ${color}20; color: ${color}; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">${item.category} • ${item.score}</span></div>
                        <div style="color: var(--text); font-size: 15px; margin-bottom: 8px; font-weight: 500;">${item.action}</div>
                        <div style="color: var(--text-muted); font-size: 13px; font-style: italic;">💡 ${item.reason}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = actionsHTML;
    } catch (e) {
        console.error("Failed to load next actions:", e);
    }
}

async function loadSalesTrends() {
    try {
        const res = await fetch('http://127.0.0.1:8000/trends/sales');
        const data = await res.json();

        const trendBadge = document.getElementById('trend-badge');
        const trendDirection = document.getElementById('trend-direction');
        const riskContainer = document.getElementById('risk-container');
        const opportunityContainer = document.getElementById('opportunity-container');

        // Trend badge with color
        const trendColors = {
            "improving": "#22c55e",
            "declining": "#f87171",
            "stable": "#f59e0b",
            "insufficient": "#94a3b8"
        };
        const color = trendColors[data.trend] || "#94a3b8";
        trendBadge.innerHTML = `<span style="color: ${color};">${data.trend_direction}</span>`;

        // Trend reason
        if (data.trend_reason) {
            trendDirection.innerHTML = `<em style="font-size: 13px;">${data.trend_reason}</em>`;
        } else {
            trendDirection.innerHTML = '';
        }

        // Risk flags
        if (data.risk_flags && data.risk_flags.length > 0) {
            const riskHTML = data.risk_flags.map(risk => {
                if (typeof risk === 'string') return `<li>${risk}</li>`;
                return `<li><strong>${risk.alert}</strong><br><em style="font-size: 12px; color: var(--text-muted);">${risk.reason}</em></li>`;
            }).join('');

            riskContainer.innerHTML = `
                <div style="background: rgba(248,113,113,0.1); border-left: 3px solid #f87171; padding: 15px; border-radius: 8px;">
                    <strong style="color: #f87171;">⚠️ Risk Alerts:</strong>
                    <ul style="margin: 10px 0 0 20px; line-height: 2;">
                        ${riskHTML}
                    </ul>
                </div>
            `;
        } else {
            riskContainer.innerHTML = `
                <div style="background: rgba(34,197,94,0.1); border-left: 3px solid #22c55e; padding: 15px; border-radius: 8px; text-align: center;">
                    ✅ <strong style="color: #22c55e;">No active risks detected</strong>
                </div>
            `;
        }

        // Opportunity flags
        if (data.opportunity_flags && data.opportunity_flags.length > 0) {
            const oppHTML = data.opportunity_flags.map(opp => {
                if (typeof opp === 'string') return `<li>${opp}</li>`;
                return `<li><strong>${opp.alert}</strong><br><em style="font-size: 12px; color: var(--text-muted);">${opp.reason}</em></li>`;
            }).join('');

            opportunityContainer.innerHTML = `
                <div style="background: rgba(34,197,94,0.1); border-left: 3px solid #22c55e; padding: 15px; border-radius: 8px;">
                    <strong style="color: #22c55e;">🎯 Opportunities:</strong>
                    <ul style="margin: 10px 0 0 20px; line-height: 2;">
                        ${oppHTML}
                    </ul>
                </div>
            `;
        } else {
            opportunityContainer.innerHTML = '';
        }
    } catch (e) {
        console.error("Failed to load sales trends:", e);
    }
}

async function loadAlerts() {
    try {
        const res = await fetch('http://127.0.0.1:8000/alerts');
        const data = await res.json();

        const container = document.getElementById('alerts-container');
        if (!data.alerts || data.alerts.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        const alertsHTML = data.alerts.map(alert => {
            const color = alert.level === 'warning' ? '#f87171' : '#60a5fa';
            return `
                <div class="card" style="margin-bottom: 15px; border: 1px solid ${color}; background: ${color}10;">
                    <h4 style="color: ${color}; margin-bottom: 5px;">${alert.message}</h4>
                    <p style="font-size: 14px; color: var(--text-muted);">${alert.reason}</p>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <h3 style="margin-bottom: 15px; color: #f87171;">⚠️ Active Alerts</h3>
            ${alertsHTML}
        `;

    } catch (e) {
        console.error("Failed to load alerts:", e);
    }
}
