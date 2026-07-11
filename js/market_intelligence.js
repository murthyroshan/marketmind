// API_BASE comes from js/app.js, which every page loads first.

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

// Terminal chart palette — one signal colour, semantic reds/greens, hairline grid.
const T = {
    amber: '#ffb020',
    amberFill: 'rgba(255, 176, 32, 0.10)',
    hot: '#ff5c4d',
    up: '#45d48a',
    cold: '#6d7f8a',
    ink: '#e8e6e2',
    faint: '#626a6e',
    grid: 'rgba(255, 255, 255, 0.05)',
    mono: "'JetBrains Mono', monospace",
};

const AXIS = {
    ticks: { color: T.faint, font: { family: T.mono, size: 10 } },
    grid: { color: T.grid, drawTicks: false },
    border: { color: 'rgba(255,255,255,0.09)' },
};

function renderCharts(data) {
    const demandCtx = document.getElementById('chartDemand').getContext('2d');
    if (demandChart) demandChart.destroy();
    demandChart = new Chart(demandCtx, {
        type: 'line',
        data: {
            labels: ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'],
            datasets: [{
                label: 'Demand Index',
                data: data.demand_trend,
                borderColor: T.amber,
                backgroundColor: T.amberFill,
                borderWidth: 1.5,
                pointBackgroundColor: T.amber,
                pointBorderWidth: 0,
                pointRadius: 2.5,
                pointHoverRadius: 5,
                tension: 0.25,
                fill: true,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 700, easing: 'easeOutCubic' },
            scales: {
                y: { beginAtZero: true, max: 120, ...AXIS },
                x: { ...AXIS, grid: { display: false } },
            },
            plugins: { legend: { display: false } },
        }
    });

    const matrixCtx = document.getElementById('chartMatrix').getContext('2d');
    if (matrixChart) matrixChart.destroy();
    matrixChart = new Chart(matrixCtx, {
        type: 'bar',
        data: {
            labels: ['COMPETITION', 'OPPORTUNITY', 'SATURATION'],
            datasets: [{
                data: [data.market_matrix.competition, data.market_matrix.opportunity, data.market_matrix.saturation],
                backgroundColor: [T.hot, T.up, T.amber],
                borderWidth: 0,
                borderRadius: 0,
                barThickness: 38,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 700, easing: 'easeOutCubic' },
            scales: {
                y: { beginAtZero: true, max: 100, ...AXIS },
                x: { ...AXIS, grid: { display: false }, ticks: { ...AXIS.ticks, color: T.ink } },
            },
            plugins: { legend: { display: false } },
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
                backgroundColor: [T.amber, T.cold, T.up, T.hot],
                borderColor: '#0d0f10',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            animation: { duration: 700, easing: 'easeOutCubic' },
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: T.faint, font: { family: T.mono, size: 10 }, boxWidth: 8, boxHeight: 8 },
                },
            },
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    analyzeMarketTrends();
});
