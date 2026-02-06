# SalesSpark AI
> **Enterprise-Grade Sales & Marketing Intelligence Engine**

## 1. Project Overview
**The Problem**: Modern sales teams are drowning in data but starving for insights. They waste hours manually researching leads, guessing which campaigns will work, and writing generic outreach emails that get ignored. Existing tools either generate robotic text or provide raw data without telling users *what to do next*.

**The Solution**: SalesSpark AI is an intelligent decision-support engine that doesn’t just generate content—it guides strategy. By combining predictive analytics, real-time lead scoring, and automated implementation tools, it empowers teams to launch high-conversion campaigns, prioritize the right leads, and close deals faster using data-backed insights rather than intuition.

## 2. Key Features

### Phase 1: Core AI Tools
- **🚀 Campaign Generator**: Creates comprehensive campaign strategies with objectives, themes, and CTAs.
- **🎯 Sales Pitch Generator**: Crafts role-specific pitches addressing problems, value props, and objections.
- **📱 Channel Content Generator**: Produces platform-perfect social posts (LinkedIn, X/Twitter, Instagram).
- **📧 AI Outreach Generator**: Drafts personalized, context-aware cold emails with follow-up tips.

### Phase 2: Intelligence & Prediction
- **⚖️ Intelligent Lead Scoring**: Deterministically scores leads (0-100) based on budget and interest, categorizing them as Hot, Warm, or Cold.
- **📊 Campaign Prediction**: Forecasts engagement, conversion probability, and risk levels before you launch.
- **🌍 Market Intelligence**: Analyzes industry trends, demand curves, and competitive landscapes in real-time.

### Phase 3: Sales Action Copilot
- **🧭 Next Best Actions**: Dynamically prioritizes your day by telling you exactly which leads to contact and how.
- **📈 Sales Momentum**: Visualizes pipeline velocity and identifies risks or opportunities.
- **🤝 Deal Closure Assistant**: Provides specific closing strategies, discount advice, and urgency drivers for active deals.
- **📅 Follow-up Planner**: Generates time-sequenced, multi-touch follow-up schedules based on lead temperature.

## 3. Tech Stack
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+)
- **Backend**: FastAPI (Python 3.9+)
- **Database**: SQLite (Zero-config, auto-initializing)
- **AI Logic**: Deterministic heuristic engines & rule-based decision trees (Mock AI for reliable, cost-free prediction)

## 4. Architecture Overview

```text
[Frontend / Browser]
       │
       ▼
[FastAPI Backend] ───► [Action Logic Engine]
       │                      │
       ▼                      ▼
[SQLite Database] ◄── [Data Processing Layer]
```

- **Zero-Dependency**: No external API keys (OpenAI/Anthropic) required.
- **Real-Time**: Logic executes instantly on request.
- **Stateful**: Data persists across sessions via SQLite.

## 5. How to Run the Project Locally

### Prerequisites
- Python 3.9+
- Git
- Web Browser (Chrome recommended)

### Step 1: Clone the Repository
```bash
git clone <your-repo-url>
cd TeamXspark
```

### Step 2: Install Backend Dependencies
```bash
pip install fastapi uvicorn pydantic
```

### Step 3: Start the Backend Server
```bash
python -m uvicorn backend.main:app --reload
```
*The server runs on `http://127.0.0.1:8000`. The database will auto-initialize on the first run.*

### Step 4: Open the Frontend
You can use any strict file server. **Do not open `index.html` directly via file:// protocol.**

**Using Python:**
```bash
# Run this in a new terminal window inside the project folder
python -m http.server 5500
```
Then visit: `http://localhost:5500`

## 6. Database Behavior
- **SQLite**: The project uses a lightweight `sales_spark.db` file.
- **Auto-Initialization**: Tables (`campaigns`, `leads`) are created automatically when the backend starts.
- **Seeding**: The system does not pre-fill data; you generate it as you use the tools.
- **Reset**: To wipe the data, simply delete `sales_spark.db` and restart the backend.

## 7. Demo Flow for Judges
1.  **Generate a Campaign**: Go to **Tools**, select "Lead Generation" on LinkedIn for a SaaS product. See the strategy appear.
2.  **Score a Lead**: Go to **Tools** > **Lead Scoring**. Enter "Acme Corp", Budget $55,000, Interest 9. see it scored as "Hot".
3.  **Predict Performance**: Go to **Prediction**. Check how a "Sales" campaign on "LinkedIn" would perform. Note the "Low Risk" assessment.
4.  **View Dashboard**: Go to **Sales Copilot**. See that Acme Corp is now your #1 "Next Best Action".
5.  **Close the Deal**: Use the **Deal Closure Assistant** (on the same page or Deal Tools) for Acme Corp to get a specific closing script.

## 8. Why SalesSpark AI is Different
Most hackathon projects are wrappers around ChatGPT that generate generic text. **SalesSpark AI is different because it focuses on Decision Intelligence.**
- It doesn't just write an email; it tells you *who* to email.
- It doesn't just guess; it uses deterministic logic to score and rank opportunities.
- It provides a closed-loop workflow: Strategy → Execution → Analysis → Action.

## 9. Future Scope
- **CRM Integrations**: Direct sync with Salesforce and HubSpot.
- **Voice Assistant**: Conversational interface for on-the-go updates.
- **Multilingual Support**: Native content generation in 30+ languages.
- **Team Collaboration**: Shared workspaces for revenue operations teams.

## 10. Team & Credits
**Team XSpark**
- Full Stack Engineering
- AI Logic & Architecture
- UI/UX Design

*Built with ❤️ for Innovation*
