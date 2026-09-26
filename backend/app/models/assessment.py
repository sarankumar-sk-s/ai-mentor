from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class AssessmentModel(BaseModel):
    """
    Domain entity for Assessments table.
    """
    id: Optional[str] = None
    profile_id: str
    assessment_type: str
    questions: List[Any] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
