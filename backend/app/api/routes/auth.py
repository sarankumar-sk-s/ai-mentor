import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, EmailStr

from app.db.supabase_client import get_supabase_client
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

@router.post("/login")
async def login(credentials: LoginRequest):
    """
    POST /api/auth/login
    Authenticates user via Supabase Auth email/password.
    """
    supabase = get_supabase_client()
    if not supabase:
        if credentials.email and len(credentials.password) >= 6:
            return {
                "access_token": f"mock_token_{credentials.email}",
                "token_type": "bearer",
                "user": {
                    "id": "mock_user_123",
                    "email": credentials.email,
                    "full_name": credentials.email.split("@")[0].capitalize()
                }
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    try:
        res = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        if not res or not res.session or not res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        user_metadata = getattr(res.user, "user_metadata", {}) or {}
        user_data = {
            "id": res.user.id,
            "email": res.user.email,
            "full_name": user_metadata.get("full_name") or res.user.email.split("@")[0].capitalize()
        }

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "token_type": "bearer",
            "user": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Supabase login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

@router.post("/signup")
@router.post("/register")
async def signup(data: SignupRequest):
    """
    POST /api/auth/signup
    Registers a new user candidate via Supabase Auth.
    """
    supabase = get_supabase_client()
    if not supabase:
        return {
            "message": "User account created successfully",
            "user": {
                "id": "mock_user_123",
                "email": data.email,
                "full_name": data.full_name or data.email.split("@")[0].capitalize()
            }
        }

    try:
        res = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name": data.full_name or ""
                }
            }
        })
        if not res or not res.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Email may already be in use."
            )

        user_metadata = getattr(res.user, "user_metadata", {}) or {}
        user_data = {
            "id": res.user.id,
            "email": res.user.email,
            "full_name": data.full_name or user_metadata.get("full_name") or res.user.email.split("@")[0].capitalize()
        }

        session_data = None
        if res.session:
            session_data = {
                "access_token": res.session.access_token,
                "refresh_token": res.session.refresh_token,
                "token_type": "bearer"
            }

        return {
            "message": "User account created successfully",
            "user": user_data,
            "session": session_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Supabase signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration error: {str(e)}"
        )

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    GET /api/auth/me
    Retrieves currently authenticated user data.
    """
    if isinstance(current_user, dict):
        return {"user": current_user}

    metadata = getattr(current_user, "user_metadata", {}) or {}
    email = getattr(current_user, "email", "")
    user_dict = {
        "id": getattr(current_user, "id", "user_id"),
        "email": email,
        "full_name": metadata.get("full_name") or (email.split("@")[0].capitalize() if email else "Candidate")
    }
    return {"user": user_dict}

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    POST /api/auth/logout
    Invalidates user auth session.
    """
    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception as e:
            logger.warning(f"Supabase sign_out notice: {e}")

    return {"message": "Logged out successfully"}

@router.get("/google")
async def google_oauth_initiate(request: Request, redirect_url: Optional[str] = None):
    """
    GET /api/auth/google
    Initiates Google OAuth authentication flow with Supabase Auth.
    Returns the OAuth authorization URL for frontend redirection.
    """
    supabase = get_supabase_client()
    target_redirect = redirect_url or "http://localhost:5173/auth/callback"

    if not supabase:
        return {
            "url": f"{target_redirect}#access_token=mock_google_token_123&token_type=bearer",
            "provider": "google"
        }

    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": target_redirect
            }
        })
        if res and hasattr(res, "url") and res.url:
            return {"url": res.url, "provider": "google"}
        raise Exception("OAuth initiation failed to return target URL")
    except Exception as e:
        logger.error(f"Google OAuth initiation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google OAuth login"
        )
