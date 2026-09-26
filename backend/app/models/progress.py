from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProgressModel(BaseModel):
    """
    Domain entity for Progress table.
    """
    id: Optional[str] = None
    profile_id: str
    skill: str
    status: str = "not_started"  # not_started, in_progress, completed
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
