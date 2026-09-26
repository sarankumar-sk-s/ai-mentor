import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """
    FastAPI TestClient fixture for app/tests.
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
