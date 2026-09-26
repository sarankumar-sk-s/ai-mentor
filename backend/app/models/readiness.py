from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReadinessScoreModel(BaseModel):
    """
    Domain entity for Readiness Scores table.
    """
    id: Optional[str] = None
    profile_id: str
    technical_score: float = Field(default=0.0, ge=0.0, le=100.0)
    skill_coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    project_score: float = Field(default=0.0, ge=0.0, le=100.0)
    assessment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    interview_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    summary: Optional[str] = None
    improvement_priorities: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
