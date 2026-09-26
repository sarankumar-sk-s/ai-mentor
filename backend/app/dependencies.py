from app.services.gemini_service import GeminiService
from app.services.profile_service import ProfileService
from app.services.skill_gap_service import SkillGapService
from app.services.roadmap_service import RoadmapService
from app.services.assessment_service import AssessmentService
from app.services.interview_service import InterviewService
from app.services.readiness_service import ReadinessService
from app.services.progress_service import ProgressService

def get_gemini_service() -> GeminiService:
    return GeminiService()

def get_profile_service() -> ProfileService:
    return ProfileService()

def get_skill_gap_service() -> SkillGapService:
    return SkillGapService()

def get_roadmap_service() -> RoadmapService:
    return RoadmapService()

def get_assessment_service() -> AssessmentService:
    return AssessmentService()

def get_interview_service() -> InterviewService:
    return InterviewService()

def get_readiness_service() -> ReadinessService:
    return ReadinessService()

def get_progress_service() -> ProgressService:
    return ProgressService()
