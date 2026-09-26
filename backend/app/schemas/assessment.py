from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AssessmentQuestionSanitizedSchema(BaseModel):
    question_id: str
    question: str
    type: str  # "mcq" | "coding" | "conceptual"
    options: Optional[List[str]] = Field(default_factory=list)
    difficulty: str
    skill: str

class AssessmentQuestionFullSchema(AssessmentQuestionSanitizedSchema):
    correct_answer: str

class AssessmentGenerateRequestSchema(BaseModel):
    profile_id: Optional[str] = Field(None, description="Optional student profile UUID")
    target_role: Optional[str] = Field("Software Engineer", description="Target role for assessment focus")
    skill_gaps: Optional[List[str]] = Field(default_factory=list, description="Candidate skill gaps to assess")
    selected_topic: Optional[str] = Field("General Software Engineering", description="Selected topic or domain")
    difficulty: Optional[str] = Field("intermediate", description="Difficulty level: beginner, intermediate, advanced, mixed")
    num_questions: Optional[int] = Field(default=5, ge=1, le=20, description="Number of questions to generate")

class CandidateAnswerSchema(BaseModel):
    question_id: str
    user_answer: str

class AssessmentSubmitRequestSchema(BaseModel):
    answers: List[CandidateAnswerSchema] = Field(..., description="List of submitted candidate answers")

class QuestionEvaluationResultSchema(BaseModel):
    question_id: str
    question: str
    type: str
    skill: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    score: float
    feedback: str

class AssessmentResultResponseSchema(BaseModel):
    assessment_id: str
    profile_id: Optional[str] = None
    target_role: str
    selected_topic: str
    difficulty: str
    overall_score: float
    total_questions: int
    correct_count: int
    weak_areas: List[str]
    overall_feedback: str
    submitted_at: Optional[str] = None
    question_evaluations: List[QuestionEvaluationResultSchema]

class AssessmentCreateSchema(BaseModel):
    profile_id: Optional[str] = None
    assessment_type: str = Field(default="technical")
    questions: List[Any] = Field(default_factory=list)
    answers: List[Any] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    feedback: Optional[str] = None

class AssessmentUpdateSchema(BaseModel):
    assessment_type: Optional[str] = None
    questions: Optional[List[Any]] = None
    answers: Optional[List[Any]] = None
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    feedback: Optional[str] = None

class AssessmentResponseSchema(BaseModel):
    id: str
    profile_id: Optional[str] = None
    assessment_type: str
    questions: List[Any]
    answers: List[Any]
    score: float
    feedback: Optional[str] = None
    created_at: Optional[str] = None
