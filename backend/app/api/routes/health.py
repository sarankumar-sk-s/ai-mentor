from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.core.database import get_supabase_client
from app.services.gemini_service import GeminiService
from app.dependencies import get_gemini_service

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", response_model=Dict[str, Any])
async def check_health(
    gemini_service: GeminiService = Depends(get_gemini_service)
):
    """
    GET /api/health
    Endpoint to check backend health status, Supabase connection, and Gemini AI configuration.
    """
    db = get_supabase_client()
    supabase_connected = db is not None
    gemini_configured = gemini_service.is_configured()

    return {
        "status": "healthy",
        "service": "PrepPilot Backend",
        "database": {
            "supabase_connected": supabase_connected
        },
        "gemini": {
            "configured": gemini_configured
        }
    }
