// ==================== PHASE 3: SALES ACTION COPILOT ====================

async function loadNextActions() {
    try {
        const res = await fetch('http://127.0.0.1:8000/actions/next');
        const data = await res.json();

        const container = document.getElementById('next-actions-container');

        if (!data.actions || data.actions.length === 0) {
            container.innerHTML = `<div class="card" style="text-align: center; padding: 40px; color: var(--text-muted);">
                📭 No actions available. Add leads to see prioritized recommendations.
            </div>`;
            return;
        }

        const priorityColors = {
            "Hot": "#f87171",
            "Warm": "#f59e0b",
            "Cold": "#22c55e"
        };

        const actionsHTML = data.actions.map(item => {
            const color = priorityColors[item.priority] || "#94a3b8";
            return `
                <div class="card" style="margin-bottom: 15px; border-left: 4px solid ${color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 700; margin-bottom: 5px;">Lead #${item.lead_id}</div>
                            <div style="color: var(--text-muted); font-size: 14px;">${item.action}</div>
                        </div>
                        <div style="background: ${color}; color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;">
                            ${item.priority}
                        </div>
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
            "stable": "#f59e0b"
        };
        const color = trendColors[data.trend] || "#94a3b8";
        trendBadge.innerHTML = `<span style="color: ${color};">${data.trend_direction}</span>`;

        // Risk flags
        if (data.risk_flags && data.risk_flags.length > 0) {
            riskContainer.innerHTML = `
                <div style="background: rgba(248,113,113,0.1); border-left: 3px solid #f87171; padding: 15px; border-radius: 8px;">
                    <strong style="color: #f87171;">⚠️ Risk Alerts:</strong>
                    <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                        ${data.risk_flags.map(flag => `<li>${flag}</li>`).join('')}
                    </ul>
                </div>
            `;
        } else {
            riskContainer.innerHTML = '';
        }

        // Opportunity flags
        if (data.opportunity_flags && data.opportunity_flags.length > 0) {
            opportunityContainer.innerHTML = `
                <div style="background: rgba(34,197,94,0.1); border-left: 3px solid #22c55e; padding: 15px; border-radius: 8px;">
                    <strong style="color: #22c55e;">🎯 Opportunities:</strong>
                    <ul style="margin: 10px 0 0 20px; line-height: 1.8;">
                        ${data.opportunity_flags.map(flag => `<li>${flag}</li>`).join('')}
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
