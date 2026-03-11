const API_BASE = "http://127.0.0.1:8000";

let demandChart = null;
let matrixChart = null;
let channelChart = null;

async function analyzeMarketTrends() {
    const industry = document.getElementById('mi_industry').value || "SaaS";
    const region = document.getElementById('mi_region').value;
    const horizon = document.getElementById('mi_horizon').value;
    const btn = document.querySelector('button');
    const originalText = btn.innerText;
    btn.innerText = "Analyzing...";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/market/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ industry, region, time_horizon: horizon })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        if (!Array.isArray(data.demand_trend) || !data.market_matrix || !data.channels) {
            throw new Error('Invalid market response shape');
        }

        renderCharts(data);
        updateInsight(data);
    } catch (e) {
        console.error("Analysis Failed", e);
        alert("Market analysis failed. Please retry after backend restart.");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

function updateInsight(data) {
    const box = document.getElementById('mi_insight_box');
    const p = document.getElementById('mi_insight_text');
    box.style.display = 'block';
    p.innerHTML = `
        <strong>Trend:</strong> ${data.market_trend_summary || 'N/A'}<br><br>
        <strong>Demand Level:</strong> ${data.demand_level || 'N/A'}<br><br>
        <strong>Competition:</strong> ${data.competition_overview || 'N/A'}<br><br>
        <strong>Opportunity:</strong> ${data.opportunity_insights || 'N/A'}
    `;
}

function renderCharts(data) {
    const demandCtx = document.getElementById('chartDemand').getContext('2d');
    if (demandChart) demandChart.destroy();
    demandChart = new Chart(demandCtx, {
        type: 'line',
        data: {
            labels: ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'],
            datasets: [{
                label: 'Market Demand Index',
                data: data.demand_trend,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 120, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            },
            plugins: { legend: { labels: { color: '#f8fafc' } } }
        }
    });

    const matrixCtx = document.getElementById('chartMatrix').getContext('2d');
    if (matrixChart) matrixChart.destroy();
    matrixChart = new Chart(matrixCtx, {
        type: 'bar',
        data: {
            labels: ['Competition', 'Opportunity', 'Saturation'],
            datasets: [{
                label: 'Market Score (0-100)',
                data: [data.market_matrix.competition, data.market_matrix.opportunity, data.market_matrix.saturation],
                backgroundColor: ['#f43f5e', '#10b981', '#f59e0b'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#f8fafc', font: { weight: 'bold' } } }
            },
            plugins: { legend: { display: false } }
        }
    });

    const channelCtx = document.getElementById('chartChannels').getContext('2d');
    if (channelChart) channelChart.destroy();
    channelChart = new Chart(channelCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data.channels),
            datasets: [{
                data: Object.values(data.channels),
                backgroundColor: ['#0a66c2', '#e1306c', '#facc15'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { color: '#f8fafc' } } }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    analyzeMarketTrends();
});
