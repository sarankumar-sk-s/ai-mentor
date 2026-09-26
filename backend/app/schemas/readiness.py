from pydantic import BaseModel, Field
from typing import List, Optional

class ReadinessCalculateRequestSchema(BaseModel):
    profile_id: str = Field(..., description="Target candidate profile UUID")
    target_role: Optional[str] = Field(None, json_schema_extra={"example": "Backend Software Engineer"})
    experience_level: Optional[str] = Field(None, json_schema_extra={"example": "beginner"})
    skills: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Python", "FastAPI", "PostgreSQL", "Git"]})
    projects: List[str] = Field(default_factory=list, json_schema_extra={"example": ["PrepPilot AI Mentor", "E-commerce Backend API"]})
    certifications: List[str] = Field(default_factory=list, json_schema_extra={"example": ["AWS Certified Developer Associate"]})

class ReadinessCalculateResponseSchema(BaseModel):
    profile_id: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    technical_score: float = Field(..., ge=0.0, le=100.0)
    skill_coverage_score: float = Field(..., ge=0.0, le=100.0)
    project_score: float = Field(..., ge=0.0, le=100.0)
    assessment_score: float = Field(..., ge=0.0, le=100.0)
    interview_score: float = Field(..., ge=0.0, le=100.0)
    source: Optional[str] = Field("gemini", description="Source of summary synthesis: 'gemini' or 'fallback'")
    summary: str
    improvement_priorities: List[str]
    created_at: Optional[str] = None

class ReadinessScoreCreateSchema(BaseModel):
    profile_id: str = Field(..., description="Target candidate profile UUID")
    technical_score: float = Field(default=0.0, ge=0.0, le=100.0)
    skill_coverage_score: float = Field(default=0.0, ge=0.0, le=100.0)
    project_score: float = Field(default=0.0, ge=0.0, le=100.0)
    assessment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    interview_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    summary: Optional[str] = None
    improvement_priorities: List[str] = Field(default_factory=list)

class ReadinessScoreUpdateSchema(BaseModel):
    technical_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    skill_coverage_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    project_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    assessment_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    interview_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    summary: Optional[str] = None
    improvement_priorities: Optional[List[str]] = None

class ReadinessScoreResponseSchema(BaseModel):
    id: str
    profile_id: str
    technical_score: float
    skill_coverage_score: float
    project_score: float
    assessment_score: float
    interview_score: float
    overall_score: float
    summary: Optional[str] = None
    improvement_priorities: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
