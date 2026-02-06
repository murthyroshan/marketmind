from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String, index=True)
    audience = Column(String)
    platform = Column(String)
    goal = Column(String)
    
    # AI Generated Fields
    objective = Column(String)
    cta = Column(String)
    outcome = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    budget = Column(Integer)
    interest = Column(Integer)
    company_size = Column(String)
    
    # AI Generated / Calculated
    score = Column(Integer)
    category = Column(String) # Hot, Warm, Cold
    
    created_at = Column(DateTime, default=datetime.utcnow)
