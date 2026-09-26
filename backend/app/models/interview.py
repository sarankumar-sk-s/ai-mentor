from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class InterviewModel(BaseModel):
    """
    Domain entity for AI Mock Interviews table.
    """
    id: Optional[str] = None
    profile_id: str
    role: str
    questions: List[Any] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
