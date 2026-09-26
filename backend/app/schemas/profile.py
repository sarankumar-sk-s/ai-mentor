from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any

class ProfileCreateSchema(BaseModel):
    user_id: Optional[str] = Field(None, description="Supabase user UUID, optional in dev mode")
    name: Optional[str] = Field(None, min_length=2, max_length=100, json_schema_extra={"example": "Alex Dev"})
    email: Optional[EmailStr] = Field(None, json_schema_extra={"example": "alex.dev@preppilot.com"})
    education: Optional[str] = Field(None, json_schema_extra={"example": "Bachelor of Technology"})
    degree: Optional[str] = Field(None, json_schema_extra={"example": "B.Tech"})
    branch: Optional[str] = Field(None, json_schema_extra={"example": "Computer Science & Engineering"})
    graduation_year: Optional[int] = Field(None, json_schema_extra={"example": 2025})
    target_role: str = Field(..., json_schema_extra={"example": "Backend Software Engineer"})
    experience_level: str = Field(..., json_schema_extra={"example": "Entry-Level"})
    skills: List[Any] = Field(default_factory=list, json_schema_extra={"example": ["Python", "FastAPI", "PostgreSQL", "Docker"]})
    interests: List[Any] = Field(default_factory=list, json_schema_extra={"example": ["AI Engineering", "Distributed Systems"]})


class ProfileUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    education: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[List[Any]] = None
    interests: Optional[List[Any]] = None

class ProfileResponseSchema(BaseModel):
    id: str
    user_id: str
    name: str
    email: EmailStr
    education: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    target_role: str
    experience_level: str
    skills: List[Any] = Field(default_factory=list)
    interests: List[Any] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ProfileAnalysisResponseSchema(BaseModel):
    profile_id: str
    status: str
    analysis: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
