from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class RoadmapWeekSchema(BaseModel):
    week: int = Field(..., description="Week number in the roadmap sequence")
    focus: str = Field(..., description="Core weekly focus or objective theme")
    skills: List[str] = Field(default_factory=list, description="Targeted skills for the week")
    topics: List[str] = Field(default_factory=list, description="Detailed topics and concepts covered")
    tasks: List[str] = Field(default_factory=list, description="Practical tasks and study exercises")
    mini_project: str = Field(..., description="Hands-on mini project or practical assignment")
    expected_outcome: str = Field(..., description="Measurable outcome or milestone for the week")

class RoadmapContentSchema(BaseModel):
    duration_weeks: int = Field(default=8, ge=1, le=52, description="Total duration of the roadmap in weeks")
    target_role: Optional[str] = Field(None, description="Target role for this roadmap")
    weeks: List[RoadmapWeekSchema] = Field(..., description="Ordered list of weekly roadmap modules")

class RoadmapGenerateRequestSchema(BaseModel):
    target_role: Optional[str] = Field(None, description="Optional override for target role")
    current_skills: Optional[List[str]] = Field(None, description="Optional override for current skills")
    skill_gaps: Optional[List[str]] = Field(None, description="Optional override for identified skill gaps")
    priority_skills: Optional[List[str]] = Field(None, description="Optional override for priority skills")
    experience_level: Optional[str] = Field(None, description="Optional override for candidate experience level")
    available_learning_time: Optional[str] = Field("10 hours/week", description="Available weekly learning time")
    duration_weeks: Optional[int] = Field(8, ge=1, le=52, description="Requested duration of roadmap in weeks")

class RoadmapGenerateResponseSchema(BaseModel):
    id: str
    profile_id: str
    target_role: Optional[str] = None
    duration_weeks: int
    roadmap_data: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RoadmapCreateSchema(BaseModel):
    profile_id: str = Field(..., description="Target candidate profile UUID")
    roadmap_data: Dict[str, Any] = Field(..., json_schema_extra={"example": {"weeks": [{"week": 1, "topic": "FastAPI Core", "status": "pending"}]}})
    duration_weeks: int = Field(default=8, ge=1, le=52)

class RoadmapUpdateSchema(BaseModel):
    roadmap_data: Optional[Dict[str, Any]] = None
    duration_weeks: Optional[int] = Field(None, ge=1, le=52)

class RoadmapResponseSchema(BaseModel):
    id: str
    profile_id: str
    roadmap_data: Dict[str, Any]
    duration_weeks: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
