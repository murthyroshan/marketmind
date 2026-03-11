# SalesSparkAI

## AI-Powered Sales Intelligence and Copilot Platform

SalesSparkAI is an AI-powered sales intelligence platform that helps teams analyze leads, generate marketing campaigns, automate outreach, and improve deal conversions with actionable insights.

The platform combines AI copilots, marketing generators, sales analytics, and deal intelligence in a single SaaS-style dashboard.

---

## Features

### AI Sales Copilot

An intelligent conversational assistant that allows users to interact with the platform naturally.

Capabilities:
- Analyze pipeline data
- Generate campaigns
- Suggest outreach messages
- Navigate the platform via chat
- Recommend next best actions

Example commands:

```text
Which leads are hot?
Create a campaign for SaaS startups
Write a cold email for founders
Show my leads
```

### Sales Copilot Dashboard

Central analytics hub displaying pipeline health.

Metrics include:
- Total Leads
- Hot Leads
- Warm Leads
- Cold Leads
- Average Lead Score

Additional insights:
- AI pipeline insights
- Sales momentum tracking
- Next best action recommendations

### AI Sales Tools

#### Campaign Generator

Generate marketing campaigns using AI.

Input:
- Product
- Platform
- Campaign goal

Output:
- Campaign theme
- Messaging strategy
- Marketing channels
- Call-to-action (CTA)
- Expected outcome

#### Sales Pitch Generator

Generate persuasive sales pitches.

Output:
- Opening hook
- Problem framing
- Product positioning
- Objection handling
- Closing statement

#### AI Outreach Generator

Generate personalized outreach emails.

Output:
- Subject line
- Email body
- Follow-up suggestion

#### Channel Content Generator

Generate social media content.

Output:
- Platform-specific captions
- Hashtags
- Tone adapted for the platform

#### Intelligent Lead Scoring

Automatically scores leads based on:
- Budget
- Interest
- Engagement signals

The platform also generates reasoning for each score.

### Campaign Performance Prediction

Predict campaign performance using pipeline metrics.

Outputs:
- Engagement prediction
- AI explanation
- Campaign improvement suggestions

### Market Intelligence

Analyze market opportunities based on product and industry context.

Outputs:
- Market trend insights
- Demand analysis
- Competition overview
- Opportunity insights

### Lead and Deal Tools

#### Lead Management

View and analyze leads stored in the system.

Lead attributes include:
- Company
- Budget
- Interest level
- Score
- Industry
- Region
- Deal stage

#### Deal Closure Assistant

AI-generated strategies for closing deals.

Outputs:
- Closing tactics
- Negotiation advice
- Recommended next step

#### Follow-Up Planner

Generate structured follow-up schedules.

Example:

```text
Day 1 -> Personalized outreach email
Day 3 -> Demo invitation
Day 7 -> ROI follow-up
```

---

## AI Copilot Capabilities

The AI Copilot acts as a product assistant for the entire platform.

It can:
- Navigate the application
- Execute tools
- Analyze sales data
- Generate marketing content
- Provide strategic insights
- Guide users through features

Example workflow:

User:

```text
Help me close more deals
```

Copilot:
1. Analyzes leads
2. Identifies top prospects
3. Suggests outreach messages
4. Recommends follow-ups

---

## Tech Stack

Frontend:
- HTML
- CSS
- JavaScript

Backend:
- Python
- FastAPI

AI Integration:
- Groq API (LLM inference)

Database:
- SQLite

Optional Integrations:
- Tavily / search APIs for market insights

---

## Database Structure

SalesSparkAI uses SQLite for lightweight storage.

### leads
Stores lead information.

Key fields include:
- company
- budget
- interest
- score
- category
- industry
- region
- deal_stage
- last_contacted
- notes

### interactions
Tracks follow-ups and communication history.

### ai_outputs
Caches AI-generated outputs to reduce repeated API calls.

---

## Project Structure

```text
TeamXspark/
|-- backend/
|   |-- main.py
|   |-- ai_service.py
|   |-- phase2_ai.py
|   |-- sales.db
|-- css/
|-- js/
|-- assets/
|-- index.html
|-- tools.html
|-- leads.html
|-- prediction.html
|-- market_intelligence.html
|-- sales_copilot.html
|-- requirements.txt
|-- .env.example
|-- README.md
```

---

## Installation and Run

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd TeamXspark
```

### 2. Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy example env file:

```powershell
Copy-Item .env.example .env
```

Then set your key in `.env`:

```env
GROQ_API_KEY=your_api_key_here
```

### 5. Run the application

Start FastAPI from the project root:

```bash
python -m uvicorn backend.main:app --reload
```

The app will run at:

```text
http://127.0.0.1:8000
```

Useful URLs:
- App: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Note: Frontend pages are served by FastAPI. You do not need a separate Live Server setup.

---

## Development Phases

Phase 1:
- AI chatbot foundation and Groq integration

Phase 2:
- Dynamic AI tools and prediction workflows

Phase 3:
- UI/UX improvements and SaaS dashboard styling

Phase 4:
- Copilot tool execution and in-app navigation

---

## Future Improvements

Possible upgrades:
- CRM integrations
- Advanced analytics dashboards
- Real-time market intelligence
- Autonomous AI sales agents
- Team collaboration features

---

## License

This project is for educational and experimental purposes.
