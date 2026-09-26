from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SkillGapModel(BaseModel):
    """
    Domain entity for Skill Gaps table.
    """
    id: Optional[str] = None
    profile_id: str
    skill: str
    current_level: str
    required_level: str
    gap_score: float = Field(ge=0.0, le=100.0)
    importance: str = "Medium"
    priority: int = 1
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
