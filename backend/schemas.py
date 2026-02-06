from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Campaign Schemas ---
class CampaignBase(BaseModel):
    product: str
    audience: str
    platform: str
    goal: str

class CampaignCreate(CampaignBase):
    pass

class CampaignResponse(CampaignBase):
    id: int
    objective: str
    cta: str
    outcome: str
    created_at: datetime
    
    # AI Insight is ephemeral, usually returned in response but not always stored directly structured. 
    # For this backend, we'll return it as part of generated response
    ai_insight: Optional[str] = None

    class Config:
        from_attributes = True

# --- Lead Schemas ---
class LeadBase(BaseModel):
    budget: int
    interest: int
    company_size: str

class LeadCreate(LeadBase):
    pass

class LeadResponse(LeadBase):
    id: int
    score: int
    category: str
    recommendation: str
    ai_insight: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Ad-hoc Generator Schemas (No DB) ---
class PitchRequest(BaseModel):
    product: str
    client_type: str

class PitchResponse(BaseModel):
    problem: str
    value_prop: str
    objection_handling: str
    closing: str
    ai_insight: str

class MarketRequest(BaseModel):
    industry: str

class MarketResponse(BaseModel):
    trend: str
    demand: str
    competition: str
    opportunity: str
    ai_insight: str

class SocialRequest(BaseModel):
    product: str
    platform: str

class SocialResponse(BaseModel):
    caption: str
    hashtags: str
    ai_insight: str

class EmailRequest(BaseModel):
    product: str
    customer_type: str
    goal: str

class EmailResponse(BaseModel):
    subject: str
    body: str
    ai_insight: str

# --- Dashboard Schema ---
class DashboardMetrics(BaseModel):
    total_campaigns: int
    total_leads: int
    hot_leads: int
    avg_lead_score: float
