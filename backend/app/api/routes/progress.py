from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any

from app.schemas.progress import (
    ProgressCreateSchema,
    ProgressUpdateSchema,
    ProgressUpdateActivityRequestSchema
)
from app.services.progress_service import ProgressService
from app.dependencies import get_progress_service
from app.dependencies.auth import get_current_user

router = APIRouter(tags=["Progress Tracking"], dependencies=[Depends(get_current_user)])


@router.get(
    "/progress/{profile_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard-Friendly Student Progress Data for Recharts Visualization"
)
async def get_dashboard_progress(
    profile_id: str,
    service: ProgressService = Depends(get_progress_service)
):
    """
    GET /api/progress/{profile_id}
    Calculates student progress percentage, tracks skill levels, assessment/interview scores,
    readiness history timeline, roadmap task completion, and learning activities.
    Returns dashboard-friendly JSON formatted for Recharts and frontend visualization.
    """
    try:
        data = await service.get_dashboard_progress(profile_id)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate dashboard progress: {str(e)}")

@router.post(
    "/progress/{profile_id}/update",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Update Student Progress & Completed Learning Activities"
)
async def update_profile_progress(
    profile_id: str,
    update_data: ProgressUpdateActivityRequestSchema,
    service: ProgressService = Depends(get_progress_service)
):
    """
    POST /api/progress/{profile_id}/update
    Updates skill completion status, records completed learning activities, appends readiness history,
    and returns updated dashboard progress JSON.
    """
    try:
        updated_dashboard = await service.update_profile_progress(profile_id, update_data)
        return {
            "message": "Progress and activity log updated successfully",
            "data": updated_dashboard
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update progress: {str(e)}")

# Backward Compatibility Endpoints for /api/progress

@router.post("/progress", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_progress(
    data: ProgressCreateSchema,
    service: ProgressService = Depends(get_progress_service)
):
    """
    POST /api/progress
    Create progress tracking record manually.
    """
    try:
        record = await service.create_progress(data)
        return {"message": "Progress record created", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create progress record: {str(e)}")

@router.get("/progress/profile/{profile_id}", response_model=Dict[str, Any])
async def list_progress_by_profile(
    profile_id: str,
    service: ProgressService = Depends(get_progress_service)
):
    """
    GET /api/progress/profile/{profile_id}
    List all skill progress trackers for profile.
    """
    records = await service.list_by_profile_id(profile_id)
    return {"data": records}

@router.put("/progress/{id}", response_model=Dict[str, Any])
async def update_progress(
    id: str,
    update_data: ProgressUpdateSchema,
    service: ProgressService = Depends(get_progress_service)
):
    """
    PUT /api/progress/{id}
    Update skill completion status and progress percentage.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return {"message": "Progress record updated", "data": updated}

@router.delete("/progress/{id}")
async def delete_progress(
    id: str,
    service: ProgressService = Depends(get_progress_service)
):
    """
    DELETE /api/progress/{id}
    Delete progress tracking record.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return {"message": "Progress record deleted"}
