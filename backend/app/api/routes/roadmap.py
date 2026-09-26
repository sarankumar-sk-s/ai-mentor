from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, Any, Optional

from app.schemas.roadmap import (
    RoadmapCreateSchema,
    RoadmapUpdateSchema,
    RoadmapGenerateRequestSchema
)
from app.services.roadmap_service import RoadmapService
from app.dependencies import get_roadmap_service
from app.dependencies.auth import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(tags=["Roadmaps"], dependencies=[Depends(get_current_user)])

@router.post(
    "/roadmap/generate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate Personalized Learning Roadmap"
)
@router.post(
    "/roadmap/generate/{profile_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate Personalized Learning Roadmap from Skill Gaps"
)
@limiter.limit("10/minute")
async def generate_roadmap_for_profile(
    request: Request,
    profile_id: Optional[str] = "default_candidate",
    body: Optional[RoadmapGenerateRequestSchema] = None,
    service: RoadmapService = Depends(get_roadmap_service)
):

    """
    POST /api/roadmap/generate or POST /api/roadmap/generate/{profile_id}
    Generate a personalized learning roadmap based on student's profile, target role,
    current skills, skill gaps, priority skills, experience level, and available learning time.
    """
    pid = profile_id or "default_candidate"
    try:
        record = await service.generate_personalized_roadmap(pid, body)
        return {
            "message": "Personalized learning roadmap generated successfully",
            "profile_id": profile_id,
            "target_role": record.get("target_role"),
            "duration_weeks": record.get("duration_weeks"),
            "data": record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate learning roadmap: {str(e)}")

@router.get(
    "/roadmap/{profile_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Latest Personalized Learning Roadmap for Profile"
)
async def get_latest_roadmap_for_profile(
    profile_id: str,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    GET /api/roadmap/{profile_id}
    Retrieve the latest personalized learning roadmap for a student profile.
    """
    record = await service.get_latest_by_profile_id(profile_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"No learning roadmap found for profile ID '{profile_id}'")
    return {
        "profile_id": profile_id,
        "target_role": record.get("target_role"),
        "duration_weeks": record.get("duration_weeks"),
        "data": record
    }

# Backward Compatibility Endpoints for /api/roadmaps

@router.post("/roadmaps", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_roadmap(
    data: RoadmapCreateSchema,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    POST /api/roadmaps
    Save a learning roadmap manually.
    """
    try:
        record = await service.create_roadmap(data)
        return {"message": "Roadmap created successfully", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create roadmap: {str(e)}")

@router.get("/roadmaps/profile/{profile_id}", response_model=Dict[str, Any])
async def get_roadmaps_by_profile(
    profile_id: str,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    GET /api/roadmaps/profile/{profile_id}
    Get all roadmaps for candidate profile.
    """
    roadmaps = await service.list_by_profile_id(profile_id)
    return {"data": roadmaps}

@router.get("/roadmaps/{id}", response_model=Dict[str, Any])
async def get_roadmap(
    id: str,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    GET /api/roadmaps/{id}
    Get roadmap by ID.
    """
    record = await service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"data": record}

@router.put("/roadmaps/{id}", response_model=Dict[str, Any])
async def update_roadmap(
    id: str,
    update_data: RoadmapUpdateSchema,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    PUT /api/roadmaps/{id}
    Update roadmap data.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"message": "Roadmap updated", "data": updated}

@router.delete("/roadmaps/{id}")
async def delete_roadmap(
    id: str,
    service: RoadmapService = Depends(get_roadmap_service)
):
    """
    DELETE /api/roadmaps/{id}
    Delete roadmap.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return {"message": "Roadmap deleted"}
