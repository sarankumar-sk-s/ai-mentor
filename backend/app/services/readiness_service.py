import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.db.supabase_client import get_supabase_client
from app.schemas.readiness import (
    ReadinessCalculateRequestSchema,
    ReadinessCalculateResponseSchema,
    ReadinessScoreCreateSchema,
    ReadinessScoreUpdateSchema
)
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

_in_memory_readiness_scores: Dict[str, Dict[str, Any]] = {}

def _ensure_uuid(val: str) -> str:
    """Safely converts string identifiers to valid UUID format for PostgreSQL UUID columns."""
    if not val:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(val))
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))

class ReadinessService:
    """
    Service layer for calculating transparent candidate readiness scores,
    synthesizing qualitative Gemini AI explanations, and persisting results in Supabase.
    """
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.db = get_supabase_client()
        self.gemini_service = gemini_service or GeminiService()

    def _calculate_deterministic_subscores(
        self,
        skills: List[str],
        target_role: str,
        projects: List[str],
        certifications: List[str],
        assessment_avg: float = 70.0,
        interview_avg: float = 70.0
    ) -> Dict[str, float]:
        """
        Transparent, Deterministic Readiness Scoring Model:
        
        1. skill_coverage_score (25% Weight):
           - Benchmark baseline role skills count: 6 required core skills.
           - Score = min(100.0, (len(set(skills)) / 6.0) * 100.0)
           
        2. technical_score (25% Weight):
           - Technical competence based on skill breadth & certifications:
           - Score = min(100.0, (len(skills) * 15.0) + (len(certifications) * 12.5))
           - Defaults to 45.0 if no skills listed.
           
        3. project_score (20% Weight):
           - Practical implementation score based on projects count:
           - Score = min(100.0, len(projects) * 35.0 + 10.0 if projects else 40.0)
           
        4. assessment_score (15% Weight):
           - Candidate assessment performance. Defaults to 70.0 if none recorded.
           
        5. interview_score (15% Weight):
           - Candidate mock interview performance. Defaults to 70.0 if none recorded.
           
        Overall Score:
           overall = 0.25 * technical_score + 0.25 * skill_coverage_score + 0.20 * project_score + 0.15 * assessment_score + 0.15 * interview_score
        """
        unique_skills = list(set([s.strip().lower() for s in skills if s.strip()]))
        num_skills = len(unique_skills)
        num_projects = len([p for p in projects if p.strip()])
        num_certs = len([c for c in certifications if c.strip()])

        skill_coverage_score = round(min(100.0, (num_skills / 6.0) * 100.0), 2)
        
        if num_skills > 0:
            tech_score_raw = (num_skills * 15.0) + (num_certs * 12.5)
            technical_score = round(min(100.0, max(45.0, tech_score_raw)), 2)
        else:
            technical_score = 45.0

        if num_projects > 0:
            project_score = round(min(100.0, (num_projects * 35.0) + 10.0), 2)
        else:
            project_score = 40.0

        assessment_score = round(max(0.0, min(100.0, assessment_avg)), 2)
        interview_score = round(max(0.0, min(100.0, interview_avg)), 2)

        overall_score = round(
            (0.25 * technical_score) +
            (0.25 * skill_coverage_score) +
            (0.20 * project_score) +
            (0.15 * assessment_score) +
            (0.15 * interview_score),
            2
        )

        return {
            "overall_score": overall_score,
            "technical_score": technical_score,
            "skill_coverage_score": skill_coverage_score,
            "project_score": project_score,
            "assessment_score": assessment_score,
            "interview_score": interview_score
        }

    async def calculate_readiness(
        self,
        data: ReadinessCalculateRequestSchema
    ) -> ReadinessCalculateResponseSchema:
        """
        Calculates student readiness scores using transparent deterministic formulas
        and synthesizes qualitative AI feedback using Gemini.
        """
        profile_uuid = _ensure_uuid(data.profile_id)
        target_role = data.target_role or "Software Engineer"
        
        # Query existing assessment and interview scores from DB if available
        assessment_avg = 70.0
        interview_avg = 70.0

        if self.db is not None:
            try:
                ass_res = self.db.table("assessments").select("score").eq("profile_id", profile_uuid).execute()
                if ass_res.data:
                    scores = [float(row["score"]) for row in ass_res.data if "score" in row]
                    if scores:
                        assessment_avg = sum(scores) / len(scores)

                int_res = self.db.table("interviews").select("overall_score").eq("profile_id", profile_uuid).execute()
                if int_res.data:
                    scores = [float(row["overall_score"]) for row in int_res.data if "overall_score" in row]
                    if scores:
                        interview_avg = sum(scores) / len(scores)
            except Exception as e:
                logger.warning(f"Could not fetch historical scores for readiness calculation ({e}). Using defaults.")

        # Compute deterministic sub-scores
        scores = self._calculate_deterministic_subscores(
            skills=data.skills,
            target_role=target_role,
            projects=data.projects,
            certifications=data.certifications,
            assessment_avg=assessment_avg,
            interview_avg=interview_avg
        )

        # Generate Gemini qualitative synthesis
        qualitative_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "improvement_priorities": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["summary", "improvement_priorities"]
        }

        prompt = f"""
        You are PrepPilot AI, an expert career mentor evaluating candidate readiness for '{target_role}'.
        
        Sub-scores (0-100 scale):
        - Overall Readiness Score: {scores['overall_score']}/100
        - Technical Competency Score: {scores['technical_score']}/100
        - Required Skill Coverage Score: {scores['skill_coverage_score']}/100
        - Practical Project Score: {scores['project_score']}/100
        - Assessment Performance Score: {scores['assessment_score']}/100
        - Mock Interview Score: {scores['interview_score']}/100

        Candidate Profile:
        - Skills: {', '.join(data.skills) if data.skills else 'None listed'}
        - Projects: {', '.join(data.projects) if data.projects else 'None listed'}
        - Certifications: {', '.join(data.certifications) if data.certifications else 'None listed'}

        Provide:
        1. 'summary': A concise 2-3 sentence qualitative evaluation explaining the readiness breakdown for '{target_role}'.
        2. 'improvement_priorities': 3 to 5 clear, concrete improvement priorities for candidate skill growth.
        """

        summary = f"Candidate scores {scores['overall_score']}/100 readiness for {target_role} with strong technical foundation."
        improvement_priorities = [
            "Expand skill coverage with containerization (Docker) and database optimization.",
            "Build a end-to-end full stack project incorporating target role technologies.",
            "Complete technical assessments and practice mock interviews to boost interview score."
        ]

        source_tag = "fallback"
        if self.gemini_service and self.gemini_service.is_configured():
            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=qualitative_schema,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict):
                    if ai_res.get("summary"):
                        summary = ai_res["summary"]
                    if ai_res.get("improvement_priorities"):
                        improvement_priorities = ai_res["improvement_priorities"]
                    source_tag = ai_res.get("_source", "gemini")
            except Exception as exc:
                logger.warning(f"Gemini qualitative synthesis failed: {exc}. Using fallback feedback.")

        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": profile_uuid,
            "technical_score": scores["technical_score"],
            "skill_coverage_score": scores["skill_coverage_score"],
            "project_score": scores["project_score"],
            "assessment_score": scores["assessment_score"],
            "interview_score": scores["interview_score"],
            "overall_score": scores["overall_score"],
            "summary": summary,
            "improvement_priorities": improvement_priorities,
            "created_at": now
        }

        if self.db is not None:
            try:
                response = self.db.table("readiness_scores").insert(record).execute()
                if response.data:
                    logger.info(f"Successfully saved readiness score record {record_id} to Supabase")
            except Exception as db_err:
                logger.warning(f"Failed to insert readiness score to Supabase ({db_err}). Storing in local repository.")

        _in_memory_readiness_scores[record_id] = record

        return ReadinessCalculateResponseSchema(
            profile_id=profile_uuid,
            overall_score=scores["overall_score"],
            technical_score=scores["technical_score"],
            skill_coverage_score=scores["skill_coverage_score"],
            project_score=scores["project_score"],
            assessment_score=scores["assessment_score"],
            interview_score=scores["interview_score"],
            source=source_tag,
            summary=summary,
            improvement_priorities=improvement_priorities,
            created_at=now
        )

    async def create_readiness_score(self, data: ReadinessScoreCreateSchema) -> Dict[str, Any]:
        profile_uuid = _ensure_uuid(data.profile_id)
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": profile_uuid,
            "raw_profile_id": data.profile_id,
            "technical_score": data.technical_score,
            "skill_coverage_score": data.skill_coverage_score,
            "project_score": data.project_score,
            "assessment_score": data.assessment_score,
            "interview_score": data.interview_score,
            "overall_score": data.overall_score,
            "summary": data.summary,
            "improvement_priorities": data.improvement_priorities,
            "created_at": datetime.now(timezone.utc).isoformat()
        }


        if self.db is not None:
            try:
                response = self.db.table("readiness_scores").insert(record).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for readiness_scores ({e}). Falling back to local store.")

        _in_memory_readiness_scores[record_id] = record
        return record

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("readiness_scores").select("*").eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase fetch failed for readiness_scores ID {record_id}: {e}")

        return _in_memory_readiness_scores.get(record_id)

    async def get_latest_by_profile_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        profile_uuid = _ensure_uuid(profile_id)
        if self.db is not None:
            try:
                response = self.db.table("readiness_scores")\
                    .select("*")\
                    .or_(f"profile_id.eq.{profile_id},profile_id.eq.{profile_uuid}")\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase query failed for readiness_scores profile {profile_id}: {e}")

        scores = [
            item for item in _in_memory_readiness_scores.values()
            if item.get("profile_id") in (profile_id, profile_uuid) or item.get("raw_profile_id") in (profile_id, profile_uuid)
        ]
        if scores:
            return sorted(scores, key=lambda x: x.get("created_at", ""), reverse=True)[0]
        return None

    async def list_by_profile_id(self, profile_id: str) -> List[Dict[str, Any]]:
        profile_uuid = _ensure_uuid(profile_id)
        if self.db is not None:
            try:
                response = self.db.table("readiness_scores")\
                    .select("*")\
                    .or_(f"profile_id.eq.{profile_id},profile_id.eq.{profile_uuid}")\
                    .execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list failed for readiness_scores profile {profile_id}: {e}")

        return [
            item for item in _in_memory_readiness_scores.values()
            if item.get("profile_id") in (profile_id, profile_uuid) or item.get("raw_profile_id") in (profile_id, profile_uuid)
        ]



    async def update(self, record_id: str, update_data: ReadinessScoreUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_by_id(record_id)

        if self.db is not None:
            try:
                response = self.db.table("readiness_scores").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for readiness_scores {record_id}: {e}")

        if record_id in _in_memory_readiness_scores:
            _in_memory_readiness_scores[record_id].update(fields_to_update)
            return _in_memory_readiness_scores[record_id]

        return None

    async def delete(self, record_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("readiness_scores").delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for readiness_scores {record_id}: {e}")

        if record_id in _in_memory_readiness_scores:
            del _in_memory_readiness_scores[record_id]
            return True
        return False
