from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, Any

from app.schemas.assessment import (
    AssessmentGenerateRequestSchema,
    AssessmentSubmitRequestSchema,
    AssessmentCreateSchema,
    AssessmentUpdateSchema
)
from app.services.assessment_service import AssessmentService
from app.dependencies import get_assessment_service
from app.dependencies.auth import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(tags=["Assessments"], dependencies=[Depends(get_current_user)])

@router.post(
    "/assessment/generate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Structured AI Technical Assessment"
)
@limiter.limit("10/minute")
async def generate_assessment(
    request: Request,
    request_data: AssessmentGenerateRequestSchema,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    POST /api/assessment/generate
    Generates a structured AI assessment based on target role, student skill gaps,
    difficulty, and selected topic. Questions include MCQ, coding, and conceptual formats.
    Correct answers are hidden prior to submission.
    """
    try:
        record = await service.generate_assessment(request_data)
        return {
            "message": "Assessment generated successfully",
            "assessment_id": record["id"],
            "data": record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate assessment: {str(e)}")

@router.get(
    "/assessment/{assessment_id}",
    response_model=Dict[str, Any],
    summary="Get Assessment by ID (Sanitized for Candidate)"
)
async def get_assessment_by_id(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    GET /api/assessment/{assessment_id}
    Retrieves assessment details. Correct answers are hidden if unsubmitted.
    """
    record = await service.get_assessment_by_id(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Assessment with ID '{assessment_id}' not found.")
    return {"data": record}

@router.post(
    "/assessment/{assessment_id}/submit",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Submit Assessment for Deterministic & Qualitative Evaluation"
)
@limiter.limit("10/minute")
async def submit_assessment(
    request: Request,
    assessment_id: str,
    submit_data: AssessmentSubmitRequestSchema,
    service: AssessmentService = Depends(get_assessment_service)
):

    """
    POST /api/assessment/{assessment_id}/submit
    Submits candidate answers. Evaluates MCQ deterministically, performs qualitative
    evaluation on coding & conceptual questions via Gemini, identifies weak areas,
    and updates readiness score inputs.
    """
    try:
        eval_result = await service.submit_assessment(assessment_id, submit_data)
        return {
            "message": "Assessment submitted and evaluated successfully",
            "assessment_id": assessment_id,
            "overall_score": eval_result["overall_score"],
            "data": eval_result
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit assessment: {str(e)}")

@router.get(
    "/assessment/{assessment_id}/result",
    response_model=Dict[str, Any],
    summary="Get Detailed Assessment Evaluation Result"
)
async def get_assessment_result(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    GET /api/assessment/{assessment_id}/result
    Retrieves complete evaluation result, per-question score breakdown, correct answers,
    and identified weak areas for a submitted assessment.
    """
    record = await service.get_by_id(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Assessment with ID '{assessment_id}' not found.")

    if record.get("status") != "submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Assessment '{assessment_id}' has not been submitted yet. Submit answers first to view results."
        )

    result_data = await service.get_assessment_result(assessment_id)
    if not result_data:
        raise HTTPException(status_code=404, detail=f"Evaluation result for assessment '{assessment_id}' is not available.")

    return {"data": result_data}

# Backward Compatibility Endpoints for /api/assessments

@router.post("/assessments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assessment(
    data: AssessmentCreateSchema,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    POST /api/assessments
    Create assessment record manually.
    """
    try:
        record = await service.create_assessment(data)
        return {"message": "Assessment created", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create assessment: {str(e)}")

@router.get("/assessments/profile/{profile_id}", response_model=Dict[str, Any])
async def list_assessments_by_profile(
    profile_id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    GET /api/assessments/profile/{profile_id}
    List assessments for profile.
    """
    records = await service.list_by_profile_id(profile_id)
    return {"data": records}

@router.get("/assessments/{id}", response_model=Dict[str, Any])
async def get_assessment(
    id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    GET /api/assessments/{id}
    Get assessment details by ID.
    """
    record = await service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"data": record}

@router.put("/assessments/{id}", response_model=Dict[str, Any])
async def update_assessment(
    id: str,
    update_data: AssessmentUpdateSchema,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    PUT /api/assessments/{id}
    Update assessment data or score.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"message": "Assessment updated", "data": updated}

@router.delete("/assessments/{id}")
async def delete_assessment(
    id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    DELETE /api/assessments/{id}
    Delete assessment.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"message": "Assessment deleted"}
