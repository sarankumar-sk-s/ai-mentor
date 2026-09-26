import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user

@pytest.fixture(autouse=True)
def override_auth():
    """
    Globally override get_current_user dependency for test suite execution.
    """
    app.dependency_overrides[get_current_user] = lambda: {"id": "test_user_id", "email": "test@preppilot.local"}
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def client():
    """
    FastAPI TestClient fixture.
    """
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_gemini_success_dict():
    """
    Mocked Gemini structured analysis output containing all 8 required fields.
    """
    return {
        "strengths": ["Strong foundational knowledge in Python"],
        "weaknesses": ["Lack of system design experience"],
        "current_skills": ["Python", "FastAPI"],
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "industry_relevant_skills": ["Docker", "Kubernetes", "CI/CD"],
        "skill_gaps": ["Docker", "PostgreSQL"],
        "priority_skills": ["Docker"],
        "recommendations": ["Build a dockerized FastAPI project."]
    }
