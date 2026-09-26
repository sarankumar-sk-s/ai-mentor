import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.database import get_supabase_client
from app.schemas.roadmap import (
    RoadmapCreateSchema,
    RoadmapUpdateSchema,
    RoadmapGenerateRequestSchema,
    RoadmapContentSchema
)
from app.services.gemini_service import GeminiService
from app.services.skill_gap_service import SkillGapService
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)

_in_memory_roadmaps: Dict[str, Dict[str, Any]] = {}

ROADMAP_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "duration_weeks": {"type": "integer"},
        "target_role": {"type": "string"},
        "weeks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "week": {"type": "integer"},
                    "focus": {"type": "string"},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "mini_project": {"type": "string"},
                    "expected_outcome": {"type": "string"}
                },
                "required": ["week", "focus", "skills", "topics", "tasks", "mini_project", "expected_outcome"]
            }
        }
    },
    "required": ["duration_weeks", "weeks"]
}

def _build_fallback_roadmap(
    target_role: str,
    skill_gaps: List[str],
    priority_skills: List[str],
    duration_weeks: int,
    available_learning_time: str
) -> Dict[str, Any]:
    gaps = skill_gaps or ["Core Role Fundamentals", "Advanced System Design", "Optimization & Testing"]
    priorities = priority_skills or gaps

    weeks = []
    for w in range(1, duration_weeks + 1):
        primary_gap = gaps[(w - 1) % len(gaps)]
        priority_skill = priorities[(w - 1) % len(priorities)]

        weeks.append({
            "week": w,
            "focus": f"Bridge Gap: {primary_gap} ({priority_skill})",
            "skills": list(dict.fromkeys([primary_gap, priority_skill])),
            "topics": [
                f"Core principles of {primary_gap}",
                f"Implementing {priority_skill} in real-world {target_role} applications",
                f"Performance tuning and debugging for {primary_gap}"
            ],
            "tasks": [
                f"Study technical documentation for {primary_gap} ({available_learning_time} pacing)",
                f"Complete 3 hands-on practical exercises focusing on {priority_skill}",
                f"Solve top {target_role} interview questions related to {primary_gap}"
            ],
            "mini_project": f"Build a practical micro-project leveraging {primary_gap} and {priority_skill}",
            "expected_outcome": f"Verified competency in {primary_gap} with a functional code implementation."
        })

    return {
        "duration_weeks": duration_weeks,
        "target_role": target_role,
        "weeks": weeks
    }

class RoadmapService:
    """
    Repository & Service layer managing personalized AI learning roadmaps in Supabase PostgreSQL.
    """
    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        skill_gap_service: Optional[SkillGapService] = None,
        profile_service: Optional[ProfileService] = None
    ):
        self.db = get_supabase_client()
        self.gemini_service = gemini_service or GeminiService()
        self.skill_gap_service = skill_gap_service or SkillGapService(gemini_service=self.gemini_service)
        self.profile_service = profile_service or ProfileService(gemini_service=self.gemini_service)

    async def generate_personalized_roadmap(
        self,
        profile_id: str,
        request_data: Optional[RoadmapGenerateRequestSchema] = None
    ) -> Dict[str, Any]:
        """
        Generates a personalized learning roadmap based on student's actual profile, skill gaps,
        priority skills, target role, experience level, and available learning time.
        Upserts/overwrites existing roadmap for the profile to allow regeneration when profile/role changes.
        """
        req = request_data or RoadmapGenerateRequestSchema()

        # Retrieve profile & skill gaps
        profile_record = await self.profile_service.get_profile_by_id(profile_id)
        gap_records = await self.skill_gap_service.list_by_profile_id(profile_id)

        profile_analysis = (profile_record.get("analysis") if profile_record else {}) or {}

        # Resolve inputs with fallback precedence: Request override -> Profile database record -> Analysis -> Default
        target_role = req.target_role or (profile_record.get("target_role") if profile_record else None) or "Software Engineer"
        experience_level = req.experience_level or (profile_record.get("experience_level") if profile_record else None) or "Entry-level"

        current_skills = req.current_skills or (profile_record.get("skills") if profile_record else None) or profile_analysis.get("current_skills") or []
        skill_gaps = req.skill_gaps or [g.get("skill") for g in gap_records if g.get("skill")] or profile_analysis.get("skill_gaps") or []
        priority_skills = req.priority_skills or profile_analysis.get("priority_skills") or skill_gaps
        available_learning_time = req.available_learning_time or "10 hours/week"
        duration_weeks = req.duration_weeks or 8

        roadmap_dict = None

        if self.gemini_service and self.gemini_service.is_configured():
            prompt = f"""
            You are an expert AI technical career mentor and curriculum designer.
            Generate a highly personalized, structured learning roadmap for a student aiming for the target role: '{target_role}'.

            Student Context & Attributes:
            - Target Role: {target_role}
            - Experience Level: {experience_level}
            - Current Skills: {', '.join(current_skills) if current_skills else 'Basic technical foundation'}
            - Identified Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'Core role competencies'}
            - Priority Skills: {', '.join(priority_skills) if priority_skills else 'High-priority gap skills'}
            - Available Weekly Study Time: {available_learning_time}
            - Requested Duration: {duration_weeks} weeks

            CRITICAL INSTRUCTIONS:
            1. DO NOT generate generic or boilerplate roadmaps.
            2. The roadmap MUST directly address and bridge the student's actual skill gaps: {', '.join(skill_gaps) if skill_gaps else 'identified gaps'}.
            3. Prioritize teaching {', '.join(priority_skills) if priority_skills else 'priority skills'} in the initial weeks.
            4. Tailor task difficulty and scope to the student's available learning time of {available_learning_time}.
            5. For each week from Week 1 to Week {duration_weeks}, provide:
               - week: (integer) week number
               - focus: main weekly theme/goal
               - skills: array of targeted skills
               - topics: array of specific technical concepts/topics
               - tasks: array of actionable study tasks & practice exercises
               - mini_project: a hands-on project applying that week's skills
               - expected_outcome: clear metric or deliverable of success

            Output MUST strictly adhere to the required JSON schema.
            """

            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=ROADMAP_GENERATION_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and "weeks" in ai_res:
                    roadmap_dict = ai_res
                    roadmap_dict["duration_weeks"] = duration_weeks
                    roadmap_dict["target_role"] = target_role
                    roadmap_dict["source"] = ai_res.get("_source", "gemini")
            except Exception as exc:
                logger.warning(f"Gemini AI roadmap generation failed: {exc}. Using deterministic gap-focused fallback roadmap.")

        if not roadmap_dict:
            roadmap_dict = _build_fallback_roadmap(
                target_role=target_role,
                skill_gaps=skill_gaps,
                priority_skills=priority_skills,
                duration_weeks=duration_weeks,
                available_learning_time=available_learning_time
            )
            roadmap_dict["source"] = "fallback"

        now = datetime.now(timezone.utc).isoformat()

        # Check if an existing roadmap exists for this profile_id (Regeneration / Update)
        existing_record = await self.get_latest_by_profile_id(profile_id)

        if existing_record:
            record_id = existing_record["id"]
            update_payload = {
                "target_role": target_role,
                "duration_weeks": duration_weeks,
                "roadmap_data": roadmap_dict,
                "updated_at": now
            }
            if self.db is not None:
                try:
                    response = self.db.table("roadmaps").update(update_payload).eq("id", record_id).execute()
                    if response.data:
                        logger.info(f"Updated existing roadmap {record_id} for profile {profile_id}")
                        return response.data[0]
                except Exception as db_err:
                    logger.warning(f"Supabase update failed for roadmap {record_id}: {db_err}")

            if record_id in _in_memory_roadmaps:
                _in_memory_roadmaps[record_id].update(update_payload)
                return _in_memory_roadmaps[record_id]

        # Insert new record if no existing record found
        record_id = str(uuid.uuid4())
        new_record = {
            "id": record_id,
            "profile_id": profile_id,
            "target_role": target_role,
            "duration_weeks": duration_weeks,
            "roadmap_data": roadmap_dict,
            "created_at": now,
            "updated_at": now
        }

        if self.db is not None:
            try:
                response = self.db.table("roadmaps").insert(new_record).execute()
                if response.data:
                    logger.info(f"Created new roadmap record {record_id} for profile {profile_id} in Supabase")
                    return response.data[0]
            except Exception as db_err:
                logger.warning(f"Supabase insert failed for roadmap {record_id}: {db_err}. Storing in memory fallback.")

        _in_memory_roadmaps[record_id] = new_record
        return new_record

    async def get_latest_by_profile_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest generated roadmap for candidate profile_id.
        """
        if self.db is not None:
            try:
                response = (
                    self.db.table("roadmaps")
                    .select("*")
                    .eq("profile_id", profile_id)
                    .order("updated_at", desc=True)
                    .execute()
                )
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase list roadmap failed for profile {profile_id}: {e}")

        matched = [r for r in _in_memory_roadmaps.values() if r.get("profile_id") == profile_id]
        if matched:
            matched.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return matched[0]
        return None

    async def create_roadmap(self, data: RoadmapCreateSchema) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": data.profile_id,
            "roadmap_data": data.roadmap_data,
            "duration_weeks": data.duration_weeks,
            "created_at": now,
            "updated_at": now,
        }

        if self.db is not None:
            try:
                response = self.db.table("roadmaps").insert(record).execute()
                if response.data:
                    logger.info(f"Created roadmap record {record_id} in Supabase")
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for roadmaps ({e}). Falling back to local store.")

        _in_memory_roadmaps[record_id] = record
        return record

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("roadmaps").select("*").eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase fetch failed for roadmaps ID {record_id}: {e}")

        return _in_memory_roadmaps.get(record_id)

    async def list_by_profile_id(self, profile_id: str) -> List[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("roadmaps").select("*").eq("profile_id", profile_id).execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list failed for roadmaps profile {profile_id}: {e}")

        return [item for item in _in_memory_roadmaps.values() if item.get("profile_id") == profile_id]

    async def update(self, record_id: str, update_data: RoadmapUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_by_id(record_id)

        fields_to_update["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            try:
                response = self.db.table("roadmaps").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for roadmaps {record_id}: {e}")

        if record_id in _in_memory_roadmaps:
            _in_memory_roadmaps[record_id].update(fields_to_update)
            return _in_memory_roadmaps[record_id]

        return None

    async def delete(self, record_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("roadmaps").delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for roadmaps {record_id}: {e}")

        if record_id in _in_memory_roadmaps:
            del _in_memory_roadmaps[record_id]
            return True
        return False
