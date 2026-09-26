from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List

from app.schemas.readiness import (
    ReadinessCalculateRequestSchema,
    ReadinessCalculateResponseSchema,
    ReadinessScoreCreateSchema,
    ReadinessScoreUpdateSchema,
    ReadinessScoreResponseSchema
)
from app.services.readiness_service import ReadinessService
from app.dependencies import get_readiness_service

router = APIRouter(prefix="/readiness", tags=["Readiness Scores"])

@router.post(
    "/calculate",
    response_model=ReadinessCalculateResponseSchema,
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "profile_id": "usr_987654321",
                        "target_role": "Backend Software Engineer",
                        "experience_level": "beginner",
                        "skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
                        "projects": ["PrepPilot AI Backend", "Attendance Tracker"],
                        "certifications": ["AWS Certified Developer Associate"]
                    }
                }
            }
        },
        "responses": {
            "200": {
                "content": {
                    "application/json": {
                        "example": {
                            "profile_id": "usr_987654321",
                            "overall_score": 78.5,
                            "technical_score": 82.5,
                            "skill_coverage_score": 66.67,
                            "project_score": 80.0,
                            "assessment_score": 70.0,
                            "interview_score": 70.0,
                            "summary": "Candidate exhibits strong core technical capability and project experience for Backend Software Engineer.",
                            "improvement_priorities": [
                                "Expand skill coverage into containerization (Docker).",
                                "Implement microservice architecture patterns."
                            ]
                        }
                    }
                }
            }
        }
    }
)
async def calculate_readiness_score(
    data: ReadinessCalculateRequestSchema,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    POST /api/readiness/calculate
    Calculates candidate career readiness scores using transparent deterministic formulas
    and generates qualitative AI feedback with Gemini.
    """
    try:
        result = await service.calculate_readiness(data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate readiness score: {str(e)}"
        )

@router.get("/profile/{profile_id}/latest", response_model=Dict[str, Any])
async def get_latest_readiness_score(
    profile_id: str,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    GET /api/readiness/profile/{profile_id}/latest
    Get latest readiness evaluation for profile ID.
    """
    record = await service.get_latest_by_profile_id(profile_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"No readiness evaluation found for profile '{profile_id}'")
    return {"data": record}

@router.get("/profile/{profile_id}", response_model=Dict[str, Any])
async def list_readiness_scores_by_profile(
    profile_id: str,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    GET /api/readiness/profile/{profile_id}
    Get all historical readiness evaluations for a profile ID.
    """
    records = await service.list_by_profile_id(profile_id)
    return {"data": records}

@router.get("/{profile_id}", response_model=Dict[str, Any])
async def get_readiness_by_profile_id(
    profile_id: str,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    GET /api/readiness/{profile_id}
    Retrieves readiness evaluation record or latest evaluation for profile ID.
    """
    record = await service.get_latest_by_profile_id(profile_id)
    if not record:
        record = await service.get_by_id(profile_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Readiness score for profile '{profile_id}' not found."
        )
    return {"data": record}

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_readiness_score(
    data: ReadinessScoreCreateSchema,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    POST /api/readiness
    Create readiness score evaluation record manually.
    """
    try:
        record = await service.create_readiness_score(data)
        return {"message": "Readiness score record created", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create readiness score: {str(e)}")

@router.put("/{id}", response_model=Dict[str, Any])
async def update_readiness_score(
    id: str,
    update_data: ReadinessScoreUpdateSchema,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    PUT /api/readiness/{id}
    Update readiness score metrics.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Readiness score record not found")
    return {"message": "Readiness score updated", "data": updated}

@router.delete("/{id}")
async def delete_readiness_score(
    id: str,
    service: ReadinessService = Depends(get_readiness_service)
):
    """
    DELETE /api/readiness/{id}
    Delete readiness score record.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Readiness score record not found")
    return {"message": "Readiness score record deleted"}
