import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import ValidationError

from app.db.supabase_client import get_supabase_client
from app.schemas.profile import ProfileCreateSchema, ProfileUpdateSchema
from app.models.profile import (
    ProfileAnalyzeRequest,
    ProfileAnalysisResult,
    ProfileAnalysisError,
    ProfileDatabaseInsertError
)

from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# In-memory fallback repository store when Supabase connection or table is unavailable
_in_memory_profiles: Dict[str, Dict[str, Any]] = {}

PROFILE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "current_skills": {"type": "array", "items": {"type": "string"}},
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "industry_relevant_skills": {"type": "array", "items": {"type": "string"}},
        "skill_gaps": {"type": "array", "items": {"type": "string"}},
        "priority_skills": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}}
    },
    "required": [
        "strengths", "weaknesses", "current_skills", "required_skills",
        "industry_relevant_skills", "skill_gaps", "priority_skills", "recommendations"
    ]
}

def _ensure_uuid(val: str) -> str:
    """Safely converts string identifiers to valid UUID format for PostgreSQL UUID columns."""
    if not val:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(val))
    except (ValueError, AttributeError):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, val))

class ProfileService:
    """
    Repository & Service layer managing profiles table operations in Supabase PostgreSQL
    and AI career readiness profile analysis via Gemini.
    """
    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.db = get_supabase_client()
        self.gemini_service = gemini_service or GeminiService()

    async def analyze_profile(self, data: ProfileAnalyzeRequest) -> ProfileAnalysisResult:
        """
        Analyzes a candidate profile using Gemini AI structured output and stores the record in Supabase.
        """
        prompt = f"""
        You are an expert AI career mentor and technical interviewer.
        Analyze the following candidate profile against their target role '{data.target_role}':

        Education: {data.degree} in {data.branch}, {data.education} (Graduation: {data.graduation_year})
        Target Role: {data.target_role}
        Experience Level: {data.experience_level}
        Current Skills: {', '.join(data.skills)}
        Interests: {', '.join(data.interests)}
        Projects: {', '.join(data.projects)}
        Certifications: {', '.join(data.certifications)}

        Explicitly cover:
        1. Current skill profile and how it maps to '{data.target_role}'.
        2. Strengths and key advantages of this candidate.
        3. Weaknesses or missing competencies.
        4. Skills relevant to the target role.
        5. Industry-relevant skills beyond what the candidate listed.
        6. Concrete skill gaps to bridge.
        7. Top priority skills to focus on first.
        8. Concrete, actionable improvement recommendations.

        Map these onto EXACTLY the 8 required JSON fields (strengths, weaknesses, current_skills, required_skills, industry_relevant_skills, skill_gaps, priority_skills, recommendations) with no extra top-level keys.
        """

        validated_result = None
        if self.gemini_service and self.gemini_service.is_configured():
            try:
                raw_result = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=PROFILE_ANALYSIS_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                raw_result["source"] = raw_result.get("source", "gemini")
                validated_result = ProfileAnalysisResult(**raw_result)
            except Exception as gen_err:
                logger.warning(f"Gemini API structured call failed or rate limited ({gen_err}). Falling back to deterministic profile analysis.")

        if not validated_result:
            skills = data.skills or ["Python", "Problem Solving"]
            target_role = data.target_role or "Software Engineer"
            fallback_dict = {
                "source": "fallback",
                "strengths": [f"Solid foundational knowledge in {', '.join(skills[:2])}", f"Proactive learning orientation towards {target_role}"],
                "weaknesses": [f"Limited production experience with advanced {target_role} frameworks", "Needs expanded test automation coverage"],
                "current_skills": skills,
                "required_skills": list(dict.fromkeys(skills + ["Docker", "PostgreSQL", "CI/CD"])),
                "industry_relevant_skills": ["Docker", "PostgreSQL", "System Architecture", "Redis"],
                "skill_gaps": ["Docker containerization", "Database query optimization"],
                "priority_skills": ["Docker", "PostgreSQL"],
                "recommendations": [
                    f"Build a hands-on project incorporating {target_role} core tools.",
                    "Complete technical assessments and practice mock interview turns."
                ]
            }
            validated_result = ProfileAnalysisResult(**fallback_dict)

        # Store profile record in Supabase database
        now = datetime.now(timezone.utc).isoformat()
        user_uuid = _ensure_uuid(data.user_id)
        profile_record = {
            "id": str(uuid.uuid4()),
            "user_id": user_uuid,
            "target_role": data.target_role,
            "experience_level": data.experience_level,
            "skills": data.skills,
            "interests": data.interests,
            "profile_data": data.model_dump(),
            "analysis": validated_result.model_dump(),
            "created_at": now,
            "updated_at": now
        }


        if self.db is not None:
            try:
                existing = self.db.table("profiles").select("id").eq("user_id", user_uuid).execute()
                if existing.data:
                    existing_id = existing.data[0]["id"]
                    update_payload = {
                        "target_role": data.target_role,
                        "experience_level": data.experience_level,
                        "skills": data.skills,
                        "interests": data.interests,
                        "profile_data": data.model_dump(),
                        "analysis": validated_result.model_dump(),
                        "updated_at": now
                    }
                    self.db.table("profiles").update(update_payload).eq("id", existing_id).execute()
                    logger.info(f"Successfully updated profile analysis for user {data.user_id} in Supabase")
                else:
                    response = self.db.table("profiles").insert(profile_record).execute()
                    if response.data:
                        logger.info(f"Successfully inserted profile analysis for user {data.user_id} in Supabase")
            except Exception as db_err:
                logger.error(f"Supabase DB operation error for profile analysis: {db_err}")
                raise ProfileDatabaseInsertError(f"Database operation failure: {str(db_err)}", validated_result)
        else:
            _in_memory_profiles[profile_record["id"]] = profile_record


        return validated_result

    async def create_profile(self, profile_data: ProfileCreateSchema) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        user_id = _ensure_uuid(profile_data.user_id or "")
        profile_id = str(uuid.uuid4())


        profile_dict = {
            "id": profile_id,
            "user_id": user_id,
            "name": profile_data.name or "Candidate",
            "email": profile_data.email or f"{user_id}@preppilot.local",
            "education": profile_data.education,
            "degree": profile_data.degree,
            "branch": profile_data.branch,
            "graduation_year": profile_data.graduation_year,
            "target_role": profile_data.target_role,
            "experience_level": profile_data.experience_level,
            "skills": profile_data.skills,
            "interests": profile_data.interests,
            "profile_data": profile_data.model_dump(),
            "created_at": now,
            "updated_at": now,
        }


        if self.db is not None:
            try:
                response = self.db.table("profiles").insert(profile_dict).execute()
                if response.data:
                    logger.info(f"Profile {profile_id} created in Supabase 'profiles' table.")
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase DB insert failed for 'profiles' table ({e}). Using in-memory repository fallback.")

        _in_memory_profiles[profile_id] = profile_dict
        logger.info(f"Profile saved to local repository store (ID: {profile_id})")
        return profile_dict

    async def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("profiles").select("*").eq("id", profile_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase select failed for profile {profile_id} ({e}). Checking local store.")

        return _in_memory_profiles.get(profile_id)

    async def list_profiles(self) -> List[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("profiles").select("*").execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list profiles failed ({e}). Returning local store.")

        return list(_in_memory_profiles.values())

    async def update_profile(self, profile_id: str, update_data: ProfileUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_profile_by_id(profile_id)

        fields_to_update["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.db is not None:
            try:
                response = self.db.table("profiles").update(fields_to_update).eq("id", profile_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for profile {profile_id} ({e}). Updating local store.")

        if profile_id in _in_memory_profiles:
            _in_memory_profiles[profile_id].update(fields_to_update)
            return _in_memory_profiles[profile_id]

        return None

    async def delete_profile(self, profile_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("profiles").delete().eq("id", profile_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for profile {profile_id}: {e}")

        if profile_id in _in_memory_profiles:
            del _in_memory_profiles[profile_id]
            return True
        return False
