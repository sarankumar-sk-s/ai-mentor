from pydantic import BaseModel, Field
from typing import List, Optional

class SkillGapItemSchema(BaseModel):
    skill: str = Field(..., json_schema_extra={"example": "Python"})
    current_level: str = Field(..., json_schema_extra={"example": "Intermediate"})
    required_level: str = Field(..., json_schema_extra={"example": "Advanced"})
    gap_score: float = Field(..., ge=0.0, le=100.0, json_schema_extra={"example": 35.0})
    importance: str = Field(..., json_schema_extra={"example": "High"})
    priority: int = Field(..., ge=1, json_schema_extra={"example": 1})
    reason: str = Field(..., json_schema_extra={"example": "Required for backend core logic development."})

class SkillGapAnalyzeRequestSchema(BaseModel):
    target_role: Optional[str] = Field(None, json_schema_extra={"example": "Backend Software Engineer"})
    skills: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Python", "SQL", "Git"]})

class SkillGapAnalyzeResponseSchema(BaseModel):
    profile_id: str
    target_role: str
    total_gaps_identified: int
    source: Optional[str] = Field("gemini", description="Source of analysis: 'gemini' or 'fallback'")
    skill_gaps: List[SkillGapItemSchema]

class SkillGapCreateSchema(BaseModel):
    profile_id: str = Field(..., description="Target candidate profile UUID")
    skill: str = Field(..., min_length=1, json_schema_extra={"example": "System Design"})
    current_level: str = Field(..., json_schema_extra={"example": "Beginner"})
    required_level: str = Field(..., json_schema_extra={"example": "Advanced"})
    gap_score: float = Field(..., ge=0.0, le=100.0, json_schema_extra={"example": 65.0})
    importance: str = Field(default="Medium", json_schema_extra={"example": "High"})
    priority: int = Field(default=1, ge=1, json_schema_extra={"example": 1})
    reason: Optional[str] = Field(None, json_schema_extra={"example": "Essential for system architecture design."})

class SkillGapUpdateSchema(BaseModel):
    skill: Optional[str] = None
    current_level: Optional[str] = None
    required_level: Optional[str] = None
    gap_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    importance: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1)
    reason: Optional[str] = None

class SkillGapResponseSchema(BaseModel):
    id: str
    profile_id: str
    skill: str
    current_level: str
    required_level: str
    gap_score: float
    importance: str
    priority: int = 1
    reason: Optional[str] = None
    created_at: Optional[str] = None
