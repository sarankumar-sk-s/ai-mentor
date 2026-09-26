import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.db.supabase_client import get_supabase_client
from app.schemas.skill_gap import (
    SkillGapItemSchema,
    SkillGapAnalyzeRequestSchema,
    SkillGapAnalyzeResponseSchema,
    SkillGapCreateSchema,
    SkillGapUpdateSchema
)
from app.services.gemini_service import GeminiService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

_in_memory_skill_gaps: Dict[str, Dict[str, Any]] = {}

def _ensure_uuid(val: str) -> str:
    """Safely converts string identifiers to valid UUID format for PostgreSQL UUID columns."""
    if not val:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(val))
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))

IMPORTANCE_RANK = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4
}

class SkillGapService:
    """
    Repository & Service layer managing Skill Gap Analysis and 'skill_gaps' table operations.
    """
    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        profile_service: Optional[ProfileService] = None
    ):
        self.db = get_supabase_client()
        self.gemini_service = gemini_service or GeminiService()
        self.profile_service = profile_service or ProfileService(gemini_service=self.gemini_service)

    def _normalize_importance(self, imp_str: str) -> str:
        s = str(imp_str).strip().capitalize()
        if s in ["Critical", "High", "Medium", "Low"]:
            return s
        if s.lower() == "urgent":
            return "Critical"
        return "Medium"

    def _validate_and_rank_gaps(self, raw_gaps: List[Dict[str, Any]]) -> List[SkillGapItemSchema]:
        """
        Backend Validation & Deterministic Sorting Engine:
        - Clamps gap_score between 0.0 and 100.0.
        - Normalizes importance to Critical, High, Medium, or Low.
        - Sorts gaps deterministically by Importance rank (Critical first) then gap_score descending.
        - Assigns priority numbers 1, 2, 3...
        """
        validated_items = []
        for item in raw_gaps:
            skill = str(item.get("skill", "Unknown Skill")).strip()
            current_level = str(item.get("current_level", "None")).strip().capitalize()
            required_level = str(item.get("required_level", "Intermediate")).strip().capitalize()
            
            try:
                raw_score = float(item.get("gap_score", 50.0))
            except (ValueError, TypeError):
                raw_score = 50.0
            gap_score = round(max(0.0, min(100.0, raw_score)), 2)
            
            importance = self._normalize_importance(item.get("importance", "Medium"))
            reason = str(item.get("reason", f"Gap identified in {skill} for target role.")).strip()

            validated_items.append({
                "skill": skill,
                "current_level": current_level,
                "required_level": required_level,
                "gap_score": gap_score,
                "importance": importance,
                "reason": reason
            })

        # Deterministic sorting: Importance rank ascending, gap_score descending
        validated_items.sort(
            key=lambda x: (
                IMPORTANCE_RANK.get(x["importance"].lower(), 3),
                -x["gap_score"]
            )
        )

        final_gaps = []
        for index, item in enumerate(validated_items, start=1):
            final_gaps.append(
                SkillGapItemSchema(
                    skill=item["skill"],
                    current_level=item["current_level"],
                    required_level=item["required_level"],
                    gap_score=item["gap_score"],
                    importance=item["importance"],
                    priority=index,
                    reason=item["reason"]
                )
            )

        return final_gaps

    async def analyze_skill_gaps(
        self,
        profile_id: str,
        request_data: Optional[SkillGapAnalyzeRequestSchema] = None
    ) -> SkillGapAnalyzeResponseSchema:
        """
        Engine comparing candidate current skills vs target role requirements.
        Uses Gemini for contextual relevance and validates numerical values deterministically.
        """
        profile_uuid = _ensure_uuid(profile_id)
        
        target_role = "Backend Software Engineer"
        candidate_skills = []

        if request_data and request_data.target_role:
            target_role = request_data.target_role
        if request_data and request_data.skills:
            candidate_skills = request_data.skills

        # Fetch profile context from DB if not provided in request
        if not candidate_skills or target_role == "Backend Software Engineer":
            db_profile = await self.profile_service.get_profile_by_id(profile_uuid)
            if db_profile:
                if not candidate_skills and db_profile.get("skills"):
                    candidate_skills = db_profile.get("skills", [])
                if target_role == "Backend Software Engineer" and db_profile.get("target_role"):
                    target_role = db_profile.get("target_role")

        prompt = f"""
        You are PrepPilot AI, an expert technical skill gap analyst.
        Analyze the candidate's skill profile against target role '{target_role}':

        Candidate Current Skills: {', '.join(candidate_skills) if candidate_skills else 'None listed'}
        Target Role: {target_role}

        Identify 4 to 7 key skill gaps comparing Current Level vs Required Level for '{target_role}'.
        For each skill gap, provide:
        - skill: Name of the technology/skill
        - current_level: Candidate's current level (None, Beginner, Intermediate, Advanced)
        - required_level: Expected level for '{target_role}' (Intermediate, Advanced, Expert)
        - gap_score: Numeric score between 0 and 100 representing the gap size
        - importance: Importance level (Critical, High, Medium, Low)
        - reason: Concise explanation why this skill gap exists and matters for '{target_role}'
        """

        schema = {
            "type": "object",
            "properties": {
                "skill_gaps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string"},
                            "current_level": {"type": "string"},
                            "required_level": {"type": "string"},
                            "gap_score": {"type": "number"},
                            "importance": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["skill", "current_level", "required_level", "gap_score", "importance", "reason"]
                    }
                }
            },
            "required": ["skill_gaps"]
        }

        raw_gaps = []
        source_tag = "fallback"

        if self.gemini_service and self.gemini_service.is_configured():
            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=schema,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and "skill_gaps" in ai_res:
                    raw_gaps = ai_res["skill_gaps"]
                    source_tag = ai_res.get("_source", "gemini")
            except Exception as e:
                logger.warning(f"Gemini skill gap AI analysis error ({e}). Using fallback gap heuristics.")

        if not raw_gaps:
            source_tag = "fallback"
            raw_gaps = [
                {
                    "skill": "Docker & Containerization",
                    "current_level": "None",
                    "required_level": "Intermediate",
                    "gap_score": 80.0,
                    "importance": "High",
                    "reason": "Essential for containerizing microservices in modern cloud deployments."
                },
                {
                    "skill": "PostgreSQL & Database Optimization",
                    "current_level": "Beginner",
                    "required_level": "Advanced",
                    "gap_score": 65.0,
                    "importance": "Critical",
                    "reason": "Core relational database design and indexing required for backend APIs."
                },
                {
                    "skill": "System Architecture & Design",
                    "current_level": "Beginner",
                    "required_level": "Advanced",
                    "gap_score": 75.0,
                    "importance": "Critical",
                    "reason": "Required to design scalable, fault-tolerant backend web services."
                }
            ]

        # Backend validation & deterministic ranking
        ranked_gaps = self._validate_and_rank_gaps(raw_gaps)

        # Delete existing skill gaps for profile in Supabase & replace with newly analyzed gaps
        if self.db is not None:
            try:
                self.db.table("skill_gaps").delete().eq("profile_id", profile_uuid).execute()
                records_to_insert = [
                    {
                        "id": str(uuid.uuid4()),
                        "profile_id": profile_uuid,
                        "skill": gap.skill,
                        "current_level": gap.current_level,
                        "required_level": gap.required_level,
                        "gap_score": gap.gap_score,
                        "importance": gap.importance,
                        "priority": gap.priority,
                        "reason": gap.reason,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    for gap in ranked_gaps
                ]
                self.db.table("skill_gaps").insert(records_to_insert).execute()
                logger.info(f"Persisted {len(records_to_insert)} skill gaps for profile {profile_uuid} in Supabase.")
            except Exception as db_err:
                logger.warning(f"Failed to persist skill gaps in Supabase ({db_err}). Storing in local repository.")

        # Update in-memory fallback store
        for gap in ranked_gaps:
            gap_id = str(uuid.uuid4())
            _in_memory_skill_gaps[gap_id] = {
                "id": gap_id,
                "profile_id": profile_uuid,
                "raw_profile_id": profile_id,
                "skill": gap.skill,
                "current_level": gap.current_level,
                "required_level": gap.required_level,
                "gap_score": gap.gap_score,
                "importance": gap.importance,
                "priority": gap.priority,
                "reason": gap.reason,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

        return SkillGapAnalyzeResponseSchema(
            profile_id=profile_uuid,
            target_role=target_role,
            total_gaps_identified=len(ranked_gaps),
            source=source_tag,
            skill_gaps=ranked_gaps
        )

    async def create_skill_gap(self, data: SkillGapCreateSchema) -> Dict[str, Any]:
        profile_uuid = _ensure_uuid(data.profile_id)
        record_id = str(uuid.uuid4())
        normalized_importance = self._normalize_importance(data.importance)
        reason = data.reason or f"Skill gap in {data.skill} required for target role."
        record = {
            "id": record_id,
            "profile_id": profile_uuid,
            "raw_profile_id": data.profile_id,
            "skill": data.skill,
            "current_level": data.current_level,
            "required_level": data.required_level,
            "gap_score": data.gap_score,
            "importance": normalized_importance,
            "priority": data.priority,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.db is not None:
            try:
                response = self.db.table("skill_gaps").insert(record).execute()
                if response.data:
                    logger.info(f"Created skill gap record {record_id} in Supabase")
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for skill_gaps ({e}). Falling back to local store.")

        _in_memory_skill_gaps[record_id] = record
        return record

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("skill_gaps").select("*").eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase fetch failed for skill_gaps ID {record_id}: {e}")

        return _in_memory_skill_gaps.get(record_id)

    async def list_by_profile_id(self, profile_id: str) -> List[Dict[str, Any]]:
        profile_uuid = _ensure_uuid(profile_id)
        if self.db is not None:
            try:
                response = self.db.table("skill_gaps")\
                    .select("*")\
                    .or_(f"profile_id.eq.{profile_id},profile_id.eq.{profile_uuid}")\
                    .order("priority", desc=False)\
                    .execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list failed for skill_gaps profile {profile_id}: {e}")

        gaps = [
            item for item in _in_memory_skill_gaps.values()
            if item.get("profile_id") in (profile_id, profile_uuid) or item.get("raw_profile_id") in (profile_id, profile_uuid)
        ]
        return sorted(gaps, key=lambda x: x.get("priority", 1))

    async def update(self, record_id: str, update_data: SkillGapUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_by_id(record_id)

        if self.db is not None:
            try:
                response = self.db.table("skill_gaps").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for skill_gaps {record_id}: {e}")

        if record_id in _in_memory_skill_gaps:
            _in_memory_skill_gaps[record_id].update(fields_to_update)
            return _in_memory_skill_gaps[record_id]

        return None

    async def delete(self, record_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("skill_gaps").delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for skill_gaps {record_id}: {e}")

        if record_id in _in_memory_skill_gaps:
            del _in_memory_skill_gaps[record_id]
            return True
        return False
