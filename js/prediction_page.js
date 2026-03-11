async function predictCampaign() {
    const platform = document.getElementById('pred_platform').value;
    const goal = document.getElementById('pred_goal').value;
    const btn = document.querySelector('button');
    const originalText = btn.innerText;

    btn.innerText = "Analyzing...";

    try {
        const res = await fetch('http://127.0.0.1:8000/predict/campaign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform, goal })
        });
        const data = await res.json();

        let riskColor = '#f59e0b';
        if (data.risk_level === 'Low') riskColor = '#22c55e';
        if (data.risk_level === 'High') riskColor = '#f87171';

        const output = `
            <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 20px;">
                <div style="flex: 1; text-align: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                    <div style="font-size: 32px; font-weight: 700; color: var(--primary);">${data.engagement_prob}%</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Predicted Engagement</div>
                </div>
                <div style="flex: 1; text-align: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                    <div style="font-size: 32px; font-weight: 700; color: var(--success);">${data.conversion_prob}%</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Conversion Probability</div>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <strong>Risk Level:</strong> <span style="color: ${riskColor}; font-weight: 700;">${data.risk_level}</span>
            </div>

            <p style="line-height: 1.6; color: var(--text); margin-bottom: 10px;"><strong>Reasoning:</strong> ${data.reasoning || data.explanation}</p>
            <p style="line-height: 1.6; color: var(--text);"><strong>Suggestions:</strong> ${data.suggestions || ''}</p>

            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: var(--text-muted);">
                Based on ${data.metrics_used.total_leads} leads, avg score ${data.metrics_used.avg_lead_score}/100, ${data.metrics_used.platform_campaigns} ${platform} campaigns, and ${data.metrics_used.goal_campaigns} ${goal} campaigns.
            </div>
        `;

        const el = document.getElementById('pred_output');
        el.style.display = 'block';
        el.innerHTML = output;
    } catch (e) {
        console.error(e);
        alert("Backend Error: Ensure server is running!");
    } finally {
        btn.innerText = originalText;
    }
}
