import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user

def test_unauthenticated_request_returns_401():
    """
    Test that calling a protected route without Authorization header returns HTTP 401.
    """
    # Temporarily remove dependency override to test actual auth dependency
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/profile")
            assert response.status_code == 401
            assert response.json() == {"detail": "Missing or invalid Authorization Bearer token"}
    finally:
        app.dependency_overrides[get_current_user] = lambda: {"id": "test_user_id"}

def test_invalid_token_returns_401():
    """
    Test that calling a protected route with an invalid Bearer token returns HTTP 401.
    """
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    mock_db = MagicMock()
    mock_db.auth.get_user.side_effect = Exception("Invalid JWT token")

    try:
        with patch("app.dependencies.auth.get_supabase_client", return_value=mock_db):
            with TestClient(app) as test_client:
                response = test_client.get(
                    "/api/profile",
                    headers={"Authorization": "Bearer invalid_token_123"}
                )
                assert response.status_code == 401
                assert response.json()["detail"] == "Invalid or expired authentication token"
    finally:
        app.dependency_overrides[get_current_user] = lambda: {"id": "test_user_id"}

def test_health_endpoint_exempt_from_auth():
    """
    Test that /api/health does not require authentication and returns 200 OK.
    """
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    finally:
        app.dependency_overrides[get_current_user] = lambda: {"id": "test_user_id"}

def test_valid_token_allows_access():
    """
    Test that a valid Supabase bearer token allows request to proceed.
    """
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    mock_user_resp = MagicMock()
    mock_user_resp.user = {"id": "usr_valid_123", "email": "valid@preppilot.local"}

    mock_db = MagicMock()
    mock_db.auth.get_user.return_value = mock_user_resp

    try:
        with patch("app.dependencies.auth.get_supabase_client", return_value=mock_db), \
             patch("app.services.profile_service.ProfileService.list_profiles", return_value=[]):
            with TestClient(app) as test_client:
                response = test_client.get(
                    "/api/profile",
                    headers={"Authorization": "Bearer valid_supabase_jwt_token"}
                )
                assert response.status_code == 200
    finally:
        app.dependency_overrides[get_current_user] = lambda: {"id": "test_user_id"}
