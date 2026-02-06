
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
