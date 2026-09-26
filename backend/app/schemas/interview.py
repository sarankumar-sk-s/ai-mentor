from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class InterviewStartRequestSchema(BaseModel):
    profile_id: Optional[str] = Field(None, description="Optional candidate profile UUID")
    target_role: str = Field(default="Software Engineer", description="Target job role for interview context")
    difficulty: Optional[str] = Field("intermediate", description="Difficulty: beginner, intermediate, advanced")
    num_questions: Optional[int] = Field(default=5, ge=1, le=10, description="Total number of interview questions")

class InterviewAnswerRequestSchema(BaseModel):
    user_answer: str = Field(..., description="Candidate's spoken or written answer text")

class TurnEvaluationSchema(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    technical_correctness: float = Field(..., ge=0.0, le=100.0)
    relevance: float = Field(..., ge=0.0, le=100.0)
    communication: float = Field(..., ge=0.0, le=100.0)
    clarity: float = Field(..., ge=0.0, le=100.0)
    completeness: float = Field(..., ge=0.0, le=100.0)
    problem_solving_approach: float = Field(..., ge=0.0, le=100.0)
    feedback: str
    source: Optional[str] = Field("gemini", description="Source of evaluation ('gemini' or 'fallback')")

class InterviewFeedbackSchema(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    technical_score: float = Field(..., ge=0.0, le=100.0)
    communication_score: float = Field(..., ge=0.0, le=100.0)
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str
    source: Optional[str] = Field("gemini", description="Source of feedback ('gemini' or 'fallback')")

class InterviewCreateSchema(BaseModel):
    profile_id: Optional[str] = None
    role: str = Field(default="Software Engineer")
    questions: List[Any] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    source: Optional[str] = Field("gemini", description="Source ('gemini' or 'fallback')")

class InterviewUpdateSchema(BaseModel):
    role: Optional[str] = None
    questions: Optional[List[Any]] = None
    answers: Optional[List[Any]] = None
    feedback: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    source: Optional[str] = None

class InterviewResponseSchema(BaseModel):
    id: str
    profile_id: Optional[str] = None
    role: str
    questions: List[Any]
    answers: List[Any]
    feedback: Dict[str, Any]
    overall_score: float
    source: Optional[str] = Field("gemini", description="Source ('gemini' or 'fallback')")
    created_at: Optional[str] = None
