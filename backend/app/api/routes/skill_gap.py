from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, Any, Optional

from app.schemas.skill_gap import (
    SkillGapAnalyzeRequestSchema,
    SkillGapAnalyzeResponseSchema,
    SkillGapCreateSchema,
    SkillGapUpdateSchema
)
from app.services.skill_gap_service import SkillGapService
from app.dependencies import get_skill_gap_service
from app.dependencies.auth import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(tags=["Skill Gaps & Analysis"], dependencies=[Depends(get_current_user)])

@router.post(
    "/skills/analyze",
    response_model=SkillGapAnalyzeResponseSchema,
    status_code=status.HTTP_200_OK
)
@router.post(
    "/skills/analyze/{profile_id}",
    response_model=SkillGapAnalyzeResponseSchema,
    status_code=status.HTTP_200_OK
)
@limiter.limit("10/minute")
async def analyze_skill_gaps(
    request: Request,
    profile_id: Optional[str] = "default_candidate",
    request_data: Optional[SkillGapAnalyzeRequestSchema] = None,
    service: SkillGapService = Depends(get_skill_gap_service)
):

    """
    POST /api/skills/analyze or POST /api/skills/analyze/{profile_id}
    Triggers Skill Gap Analysis engine comparing current candidate skills against target role requirements.
    Validates numerical gap scores, normalizes importance, and assigns deterministic priority ranks.
    """
    pid = profile_id or "default_candidate"
    try:
        result = await service.analyze_skill_gaps(pid, request_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze skill gaps: {str(e)}"
        )

@router.get(
    "/skills/gaps/{profile_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK
)
async def get_skill_gaps_for_profile(
    profile_id: str,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    GET /api/skills/gaps/{profile_id}
    Retrieves all identified skill gaps for a candidate profile sorted by priority rank.
    """
    gaps = await service.list_by_profile_id(profile_id)
    return {"data": gaps}

@router.post("/skill-gaps", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_skill_gap(
    data: SkillGapCreateSchema,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    POST /api/skill-gaps
    Create a skill gap record manually.
    """
    try:
        record = await service.create_skill_gap(data)
        return {"message": "Skill gap record created", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create skill gap: {str(e)}")

@router.get("/skill-gaps/profile/{profile_id}", response_model=Dict[str, Any])
async def list_skill_gaps_by_profile(
    profile_id: str,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    GET /api/skill-gaps/profile/{profile_id}
    List all skill gaps for a candidate profile.
    """
    gaps = await service.list_by_profile_id(profile_id)
    return {"data": gaps}

@router.get("/skill-gaps/{id}", response_model=Dict[str, Any])
async def get_skill_gap(
    id: str,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    GET /api/skill-gaps/{id}
    Get skill gap by ID.
    """
    record = await service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Skill gap record not found")
    return {"data": record}

@router.put("/skill-gaps/{id}", response_model=Dict[str, Any])
async def update_skill_gap(
    id: str,
    update_data: SkillGapUpdateSchema,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    PUT /api/skill-gaps/{id}
    Update a skill gap record.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Skill gap record not found")
    return {"message": "Skill gap record updated", "data": updated}

@router.delete("/skill-gaps/{id}")
async def delete_skill_gap(
    id: str,
    service: SkillGapService = Depends(get_skill_gap_service)
):
    """
    DELETE /api/skill-gaps/{id}
    Delete a skill gap record.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill gap record not found")
    return {"message": "Skill gap record deleted"}
