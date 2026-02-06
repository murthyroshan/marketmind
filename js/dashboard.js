/**
 * Dashboard Logic
 * Fetches real-time metrics from FastAPI Backend
 */

const API_URL = "http://127.0.0.1:8000/dashboard";

async function renderDashboard() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error("Backend not reachable");

        const data = await res.json();

        // NEW RESPONSE FORMAT: data.data_source and data.metrics
        const metrics = data.metrics || data; // Fallback for backwards compat
        const dataSource = data.data_source || "Live Database";

        // Display data source badge
        const isLive = dataSource === "Live Database";
        const badgeEl = document.getElementById('data-source-badge');
        if (badgeEl) {
            const icon = isLive ? "🟢" : "🟡";
            const color = isLive ? "#22c55e" : "#f59e0b";
            badgeEl.innerHTML = `
                <div style="background: ${color}15; border: 1px solid ${color}; color: ${color}; padding: 6px 14px; border-radius: 16px; font-size: 12px; font-weight: 600; display: inline-block;">
                    ${icon} ${dataSource}
                </div>
            `;
        }

        // 1. Update Counters
        updateCounter('dash-campaigns', metrics.total_campaigns);
        updateCounter('dash-leads', metrics.total_leads);
        updateCounter('dash-hot', metrics.hot_leads);
        updateCounter('dash-quality', metrics.avg_lead_score + '%');

        // 2. Trend Analysis
        updateTrend('trend-campaigns', metrics.total_campaigns, 5, "📈 High Activity Volume", "🟡 Moderate Activity");

        // Hot Lead Trend
        const trendHot = document.getElementById('trend-hot');
        if (metrics.total_leads > 0) {
            let hotRatio = metrics.hot_leads / metrics.total_leads;
            if (hotRatio > 0.3) {
                trendHot.innerHTML = "🔥 High Conversion Potential";
                trendHot.style.color = "var(--success)";
            } else {
                trendHot.innerHTML = "❄️ Needs Better Targeting";
                trendHot.style.color = "var(--warning)";
            }
        } else {
            trendHot.innerHTML = "Waiting for data...";
        }

        // Quality Trend - Use backend-computed value if available
        const trendQuality = document.getElementById('trend-quality');
        if (metrics.lead_quality_trend) {
            const trendIcons = {
                "Improving": "📈",
                "Declining": "📉",
                "Stable": "➡️"
            };
            trendQuality.innerHTML = `${trendIcons[metrics.lead_quality_trend]} ${metrics.lead_quality_trend}`;
        } else {
            if (metrics.avg_lead_score > 70) trendQuality.innerHTML = "✅ Premium Lead Quality";
            else if (metrics.avg_lead_score > 40) trendQuality.innerHTML = "⚠️ Mixed Lead Quality";
            else trendQuality.innerHTML = "🔻 Low Quality Detect";
        }

        // 3. Render Chart
        renderChart(metrics.avg_lead_score);

        // 4. Display Best Platform if available
        if (metrics.best_platform) {
            const platformEl = document.getElementById('best-platform');
            if (platformEl) {
                platformEl.innerText = metrics.best_platform;
            }
        }

        // PHASE 2: Load Intelligence Features
        await loadRecommendations();
        await loadSegments();
        await loadWeeklyReport();

        // PHASE 3: Load Sales Action Copilot
        await loadNextActions();
        await loadSalesTrends();
        await loadAlerts();

    } catch (e) {
        console.error("Dashboard Sync Failed:", e);
        // Fallback for demo if backend is offline
        document.getElementById('trend-campaigns').innerText = "⚠️ Backend Offline";
    }
}

function updateCounter(id, value) {
    document.getElementById(id).innerText = value;
}

function updateTrend(id, value, threshold, highMsg, lowMsg) {
    const el = document.getElementById(id);
    if (value > threshold) {
        el.innerHTML = highMsg;
        el.style.color = "var(--success)";
    } else {
        el.innerHTML = lowMsg;
        el.style.color = "var(--text-muted)";
    }
}

function renderChart(avgScore) {
    const chartContainer = document.getElementById('simple-chart');
    if (!chartContainer) return;

    chartContainer.innerHTML = `
        <div style="margin-top:20px; text-align:left;">
            <div style="font-size:12px; margin-bottom:5px; color:#94a3b8;">AVG LEAD SCORE PERFORMANCE</div>
            <div style="width:100%; height:20px; background:rgba(255,255,255,0.1); border-radius:10px; overflow:hidden;">
                <div style="width:${Math.min(100, avgScore)}%; height:100%; background: linear-gradient(90deg, var(--primary), var(--success)); transition: width 1s;"></div>
            </div>
            <div style="font-size:12px; margin-top:5px; color:#94a3b8; display:flex; justify-content:space-between;">
                <span>0</span><span>100</span>
            </div>
        </div>
    `;
}

// ==================== PHASE 2: INTELLIGENCE LAYER ====================

async function loadRecommendations() {
    try {
        const res = await fetch('http://127.0.0.1:8000/recommendations');
        const data = await res.json();

        document.getElementById('rec_action').innerText = data.priority_action;
        document.getElementById('rec_tip').innerText = data.strategy_tip;
        document.getElementById('rec_platform').innerHTML = `<strong>Best Platform:</strong> ${data.best_platform}`;
    } catch (e) {
        console.error("Failed to load recommendations:", e);
    }
}

async function loadSegments() {
    try {
        const res = await fetch('http://127.0.0.1:8000/segments');
        const data = await res.json();

        document.getElementById('seg_high').innerText = data.high_value;
        document.getElementById('seg_intent').innerText = data.high_intent;
        document.getElementById('seg_price').innerText = data.price_sensitive;
        document.getElementById('seg_low').innerText = data.low_intent;
    } catch (e) {
        console.error("Failed to load segments:", e);
    }
}

async function loadWeeklyReport() {
    try {
        const res = await fetch('http://127.0.0.1:8000/weekly-report');
        const data = await res.json();

        document.getElementById('report_summary').innerText = data.summary;
        const trendIcon = data.trend === 'up' ? '📈' : data.trend === 'down' ? '📉' : '➡️';
        document.getElementById('report_meta').innerHTML = `${trendIcon} Trend: <strong>${data.trend.toUpperCase()}</strong> | Best: <strong>${data.best_platform}</strong> | Hot Leads: <strong>${data.hot_leads}</strong>`;
    } catch (e) {
        console.error("Failed to load weekly report:", e);
    }
}

// Initial Render
document.addEventListener('DOMContentLoaded', renderDashboard);

// Auto-refresh every 5 seconds for "Real-time" feel
setInterval(renderDashboard, 5000);
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

        // Risk flags - handle objects
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

        // Opportunity flags - handle objects
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

        const alertsContainer = document.getElementById('alerts-container');

        if (!alertsContainer) return; // Container doesn't exist yet

        if (!data.alerts || data.alerts.length === 0) {
            // Hide section if no alerts
            alertsContainer.style.display = 'none';
            return;
        }

        alertsContainer.style.display = 'block';

        const alertsHTML = data.alerts.map(alert => {
            const levelColors = {
                "warning": "#f59e0b",
                "error": "#f87171",
                "info": "#60a5fa"
            };
            const color = levelColors[alert.level] || "#94a3b8";

            return `
                <div style="background: ${color}15; border-left: 3px solid ${color}; padding: 12px 15px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="font-weight: 600; color: ${color}; margin-bottom: 5px;">
                        ${alert.message}
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); font-style: italic;">
                        ${alert.reason}
                    </div>
                </div>
            `;
        }).join('');

        alertsContainer.innerHTML = `
            <div style="margin-bottom: 15px;">
                <strong style="font-size: 14px;">🚨 Active Alerts:</strong>
            </div>
            ${alertsHTML}
        `;
    } catch (e) {
        console.error("Failed to load alerts:", e);
    }
}
