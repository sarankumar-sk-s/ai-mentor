from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Literal, Any, Dict
from datetime import datetime

class ProfileAnalysisError(Exception):
    """Raised when profile analysis validation or LLM generation fails."""
    pass

class ProfileDatabaseInsertError(Exception):
    """Raised when database insertion fails after profile analysis is successfully generated."""
    def __init__(self, message: str, analysis: Any):
        super().__init__(message)
        self.analysis = analysis

class ProfileAnalyzeRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    education: str
    degree: str
    branch: str
    graduation_year: int
    target_role: str
    experience_level: Literal["beginner", "intermediate", "advanced"]
    skills: List[str]
    interests: List[str]
    projects: List[str]
    certifications: List[str]


class ProfileAnalysisResult(BaseModel):
    source: Optional[str] = Field("gemini", description="Source of analysis: 'gemini' or 'fallback'")
    strengths: List[str]
    weaknesses: List[str]
    current_skills: List[str]
    required_skills: List[str]
    industry_relevant_skills: List[str]
    skill_gaps: List[str]
    priority_skills: List[str]
    recommendations: List[str]

class ProfileModel(BaseModel):
    """
    Domain entity for User Profiles table.
    """
    id: Optional[str] = None
    user_id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    education: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    skills: List[Any] = Field(default_factory=list)
    interests: List[Any] = Field(default_factory=list)
    profile_data: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
