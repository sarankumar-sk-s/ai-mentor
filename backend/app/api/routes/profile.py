from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List

from app.models.profile import (
    ProfileAnalyzeRequest,
    ProfileAnalysisResult,
    ProfileAnalysisError,
    ProfileDatabaseInsertError
)
from app.schemas.profile import (
    ProfileCreateSchema,
    ProfileUpdateSchema
)
from app.services.profile_service import ProfileService
from app.dependencies import get_profile_service
from app.dependencies.auth import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(prefix="/profile", tags=["Profile"], dependencies=[Depends(get_current_user)])

@router.post(
    "/analyze",
    response_model=ProfileAnalysisResult,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "usr_987654321",
                        "education": "Bachelor of Technology",
                        "degree": "B.Tech",
                        "branch": "Computer Science & Engineering",
                        "graduation_year": 2025,
                        "target_role": "Backend Software Engineer",
                        "experience_level": "beginner",
                        "skills": ["Python", "FastAPI", "SQL"],
                        "interests": ["Backend Systems", "Distributed Databases"],
                        "projects": ["PrepPilot AI Mentor", "E-commerce Backend API"],
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
                            "strengths": ["Strong core foundation in Python and FastAPI"],
                            "weaknesses": ["Limited hands-on experience with production containerization"],
                            "current_skills": ["Python", "FastAPI", "SQL"],
                            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
                            "industry_relevant_skills": ["Docker", "Kubernetes", "CI/CD Pipelines", "Redis"],
                            "skill_gaps": ["Docker containerization", "Redis caching"],
                            "priority_skills": ["Docker", "PostgreSQL schema design"],
                            "recommendations": [
                                "Build a containerized FastAPI application with PostgreSQL & Redis.",
                                "Study system design principles for scalable backend services."
                            ]
                        }
                    }
                }
            }
        }
    }
)
@limiter.limit("10/minute")
async def analyze_profile(
    request: Request,
    data: ProfileAnalyzeRequest,
    service: ProfileService = Depends(get_profile_service)
):

    """
    POST /api/profile/analyze
    Analyzes candidate profile using Gemini AI structured output and stores record in Supabase.

    Example Request Body:
    ```json
    {
        "user_id": "usr_987654321",
        "education": "Bachelor of Technology",
        "degree": "B.Tech",
        "branch": "Computer Science & Engineering",
        "graduation_year": 2025,
        "target_role": "Backend Software Engineer",
        "experience_level": "beginner",
        "skills": ["Python", "FastAPI", "SQL"],
        "interests": ["Backend Systems", "Distributed Databases"],
        "projects": ["PrepPilot AI Mentor", "E-commerce Backend API"],
        "certifications": ["AWS Certified Developer Associate"]
    }
    ```

    Example Response Body:
    ```json
    {
        "strengths": ["Strong core foundation in Python and FastAPI"],
        "weaknesses": ["Limited hands-on experience with production containerization"],
        "current_skills": ["Python", "FastAPI", "SQL"],
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
        "industry_relevant_skills": ["Docker", "Kubernetes", "CI/CD Pipelines", "Redis"],
        "skill_gaps": ["Docker containerization", "Redis caching"],
        "priority_skills": ["Docker", "PostgreSQL schema design"],
        "recommendations": [
            "Build a containerized FastAPI application with PostgreSQL & Redis.",
            "Study system design principles for scalable backend services."
        ]
    }
    ```
    """
    try:
        analysis_result = await service.analyze_profile(data)
        return analysis_result
    except ProfileAnalysisError as pae:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "analysis_failed", "detail": str(pae)}
        )
    except ProfileDatabaseInsertError as pdie:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "database_insert_failed",
                "detail": str(pdie),
                "analysis": pdie.analysis.model_dump()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during profile analysis: {str(e)}"
        )

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreateSchema,
    service: ProfileService = Depends(get_profile_service)
):
    """
    POST /api/profile
    Create a user candidate profile.
    """
    try:
        profile = await service.create_profile(profile_data)
        return {
            "message": "Profile created successfully",
            "data": profile
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}"
        )

@router.get("", response_model=Dict[str, Any])
async def list_profiles(
    service: ProfileService = Depends(get_profile_service)
):
    """
    GET /api/profile
    List all user candidate profiles.
    """
    profiles = await service.list_profiles()
    return {"data": profiles}

@router.get("/{profile_id}", response_model=Dict[str, Any])
async def get_profile(
    profile_id: str,
    service: ProfileService = Depends(get_profile_service)
):
    """
    GET /api/profile/{profile_id}
    Retrieve user profile by ID.
    """
    profile = await service.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found."
        )
    return {"data": profile}

@router.put("/{profile_id}", response_model=Dict[str, Any])
async def update_profile(
    profile_id: str,
    update_data: ProfileUpdateSchema,
    service: ProfileService = Depends(get_profile_service)
):
    """
    PUT /api/profile/{profile_id}
    Update user candidate profile.
    """
    updated_profile = await service.update_profile(profile_id, update_data)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found."
        )
    return {"message": "Profile updated successfully", "data": updated_profile}

@router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
async def delete_profile(
    profile_id: str,
    service: ProfileService = Depends(get_profile_service)
):
    """
    DELETE /api/profile/{profile_id}
    Delete user candidate profile.
    """
    success = await service.delete_profile(profile_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found."
        )
    return {"message": "Profile deleted successfully"}
