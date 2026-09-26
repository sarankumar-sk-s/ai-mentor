from fastapi import APIRouter, HTTPException, Depends, status, Request
from typing import Dict, Any, Optional

from app.schemas.interview import (
    InterviewStartRequestSchema,
    InterviewAnswerRequestSchema,
    InterviewCreateSchema,
    InterviewUpdateSchema
)
from app.services.interview_service import InterviewService
from app.dependencies import get_interview_service
from app.dependencies.auth import get_current_user
from app.core.rate_limit import limiter

router = APIRouter(tags=["Interviews"], dependencies=[Depends(get_current_user)])

@router.post(
    "/interview/start",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Start AI-Powered Mock Interview Session"
)
@limiter.limit("10/minute")
async def start_interview(
    request: Request,
    request_data: InterviewStartRequestSchema,
    service: InterviewService = Depends(get_interview_service)
):
    """
    POST /api/interview/start
    Starts an interactive mock interview session server-side. Generates Turn 1 question
    using Gemini AI based on target role, candidate profile, and skill gaps.
    """
    try:
        record = await service.start_interview(request_data)
        turns = record.get("turns", [])
        question_1 = turns[0].get("question") if turns else None
        return {
            "message": "Mock interview session started successfully",
            "interview_id": record["id"],
            "target_role": record.get("role"),
            "current_turn": record.get("current_turn", 1),
            "total_questions": record.get("num_questions", 5),
            "question": question_1,
            "data": record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview session: {str(e)}")

@router.post(
    "/interview/{interview_id}/answer",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Submit Candidate Turn Answer for Evaluation & Get Next Question"
)
@limiter.limit("10/minute")
async def submit_interview_answer(
    request: Request,
    interview_id: str,
    answer_data: InterviewAnswerRequestSchema,
    service: InterviewService = Depends(get_interview_service)
):
    """
    POST /api/interview/{interview_id}/answer
    Submits candidate's answer for the current turn. Evaluates answer across 6 criteria via Gemini,
    updates conversation history server-side, and generates the next interview question.
    """
    try:
        result = await service.submit_answer(interview_id, answer_data)
        return {
            "message": "Answer recorded and evaluated successfully",
            "data": result
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process interview answer: {str(e)}")

@router.post(
    "/interview/{interview_id}/next",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Next Interview Question / Current Turn State"
)
async def get_next_interview_question(
    interview_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """
    POST /api/interview/{interview_id}/next
    Retrieves current turn question and status for active interview session.
    """
    try:
        state = await service.get_next_question(interview_id)
        return {
            "message": "Current turn state retrieved",
            "data": state
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch next question: {str(e)}")

@router.post(
    "/interview/{interview_id}/finish",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Finish Interview Session & Synthesize Final Feedback"
)
@limiter.limit("10/minute")
async def finish_interview_session(
    request: Request,
    interview_id: str,
    service: InterviewService = Depends(get_interview_service)
):

    """
    POST /api/interview/{interview_id}/finish
    Concludes the mock interview session. Gemini synthesizes final comprehensive feedback JSON:
    overall_score, technical_score, communication_score, confidence_score, strengths, weaknesses,
    recommendations, and executive summary. Handles interrupted sessions gracefully.
    """
    try:
        feedback = await service.finish_interview(interview_id)
        return {
            "message": "Interview session completed and evaluated successfully",
            "interview_id": interview_id,
            "overall_score": feedback.get("overall_score", 0.0),
            "data": feedback
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finish interview session: {str(e)}")

@router.get(
    "/interview/{interview_id}/feedback",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Final Structured Feedback for Mock Interview"
)
async def get_interview_feedback(
    interview_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """
    GET /api/interview/{interview_id}/feedback
    Retrieves synthesized interview feedback object for candidate review.
    """
    try:
        feedback = await service.get_interview_feedback(interview_id)
        return {
            "interview_id": interview_id,
            "data": feedback
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve interview feedback: {str(e)}")

# Backward Compatibility Endpoints for /api/interviews

@router.post("/interviews", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_interview(
    data: InterviewCreateSchema,
    service: InterviewService = Depends(get_interview_service)
):
    """
    POST /api/interviews
    Create mock interview session manually.
    """
    try:
        record = await service.create_interview(data)
        return {"message": "Interview session created", "data": record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create interview session: {str(e)}")

@router.get("/interviews/profile/{profile_id}", response_model=Dict[str, Any])
async def list_interviews_by_profile(
    profile_id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """
    GET /api/interviews/profile/{profile_id}
    List interviews for candidate profile.
    """
    records = await service.list_by_profile_id(profile_id)
    return {"data": records}

@router.get("/interviews/{id}", response_model=Dict[str, Any])
async def get_interview(
    id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """
    GET /api/interviews/{id}
    Get interview session details.
    """
    record = await service.get_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return {"data": record}

@router.put("/interviews/{id}", response_model=Dict[str, Any])
async def update_interview(
    id: str,
    update_data: InterviewUpdateSchema,
    service: InterviewService = Depends(get_interview_service)
):
    """
    PUT /api/interviews/{id}
    Update interview session feedback or scores.
    """
    updated = await service.update(id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return {"message": "Interview session updated", "data": updated}

@router.delete("/interviews/{id}")
async def delete_interview(
    id: str,
    service: InterviewService = Depends(get_interview_service)
):
    """
    DELETE /api/interviews/{id}
    Delete interview session.
    """
    success = await service.delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return {"message": "Interview session deleted"}
