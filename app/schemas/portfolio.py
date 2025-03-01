from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.db_models import PortfolioStatus
from typing import Optional, Dict, Any



class PortfolioURL(BaseModel):
    linkedin_url: Optional[str] = Field(None, description="URL of the LinkedIn profile")
    github_url: str = Field('....', description="URL of the github profile")


class PortfolioCreate(BaseModel):
    user_id: UUID
    linkedin_url: Optional[str] = Field(None, description="URL to user's LinkedIn profile")
    github_url: Optional[str] = Field(None, description="URL to user's GitHub profile")
    linkedin_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from LinkedIn")
    github_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from GitHub")

class PortfolioUpdate(BaseModel):
    linkedin_url: Optional[str] = Field(None, description="URL to user's LinkedIn profile")
    github_url: Optional[str] = Field(None, description="URL to user's GitHub profile")
    linkedin_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from LinkedIn")
    github_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from GitHub")

class Portfolio(BaseModel):
    id: UUID
    user_id: UUID
    linkedin_url: Optional[str] = Field(None, description="URL to user's LinkedIn profile")
    github_url: Optional[str] = Field(None, description="URL to user's GitHub profile")
    linkedin_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from LinkedIn")
    github_data: Optional[Dict[str, Any]] = Field(None, description="JSON data from GitHub")
    upload_date: datetime
    status: PortfolioStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True




