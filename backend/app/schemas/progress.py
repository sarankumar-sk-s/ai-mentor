from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SkillProgressItemSchema(BaseModel):
    skill: str
    progress: float = Field(..., ge=0.0, le=100.0)
    status: str  # "Not Started" | "In Progress" | "Completed"

class AssessmentProgressSummarySchema(BaseModel):
    average_score: float = 0.0
    total_assessments: int = 0
    completed_assessments: int = 0
    recent_scores: List[Dict[str, Any]] = Field(default_factory=list)

class InterviewProgressSummarySchema(BaseModel):
    average_score: float = 0.0
    total_interviews: int = 0
    completed_interviews: int = 0
    recent_scores: List[Dict[str, Any]] = Field(default_factory=list)

class ReadinessHistoryPointSchema(BaseModel):
    date: str
    score: float

class RoadmapProgressSummarySchema(BaseModel):
    completed_tasks: int = 0
    total_tasks: int = 0
    percentage: float = 0.0

class LearningActivitySchema(BaseModel):
    activity_id: str
    type: str
    title: str
    completed_at: str

class ProgressDashboardResponseSchema(BaseModel):
    profile_id: str
    overall_progress: int = Field(..., ge=0, le=100)
    skills: List[SkillProgressItemSchema] = Field(default_factory=list)
    assessment_progress: AssessmentProgressSummarySchema
    interview_progress: InterviewProgressSummarySchema
    readiness_history: List[ReadinessHistoryPointSchema] = Field(default_factory=list)
    roadmap_progress: RoadmapProgressSummarySchema
    completed_activities: List[LearningActivitySchema] = Field(default_factory=list)
    updated_at: Optional[str] = None

class ProgressUpdateActivityRequestSchema(BaseModel):
    skill: Optional[str] = None
    status: Optional[str] = None  # "not_started" | "in_progress" | "completed"
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    roadmap_task: Optional[Dict[str, Any]] = None
    activity: Optional[Dict[str, Any]] = None
    readiness_score: Optional[float] = Field(None, ge=0.0, le=100.0)

class ProgressCreateSchema(BaseModel):
    profile_id: str = Field(..., description="Target candidate profile UUID")
    skill: str = Field(..., min_length=1)
    status: str = Field(default="not_started")
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

class ProgressUpdateSchema(BaseModel):
    status: Optional[str] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)

class ProgressResponseSchema(BaseModel):
    id: str
    profile_id: str
    skill: str
    status: str
    progress_percentage: float
    updated_at: Optional[str] = None
