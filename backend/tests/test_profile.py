import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.models.profile import ProfileAnalysisResult

@pytest.fixture
def mock_gemini_success_dict():
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

def test_profile_analyze_success(client, mock_gemini_success_dict):
    """
    Test valid request to POST /api/profile/analyze returns 200 with all 8 expected keys.
    """
    payload = {
        "user_id": "user_test_001",
        "education": "Bachelor of Engineering",
        "degree": "B.E.",
        "branch": "Computer Science",
        "graduation_year": 2025,
        "target_role": "Backend Engineer",
        "experience_level": "beginner",
        "skills": ["Python", "FastAPI"],
        "interests": ["Cloud"],
        "projects": ["PrepPilot"],
        "certifications": ["AWS Cloud Practitioner"]
    }

    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.profile_service.get_supabase_client", return_value=mock_db):
        
        mock_gen.return_value = mock_gemini_success_dict
        
        response = client.post("/api/profile/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = [
            "strengths", "weaknesses", "current_skills", "required_skills",
            "industry_relevant_skills", "skill_gaps", "priority_skills", "recommendations"
        ]
        for key in expected_keys:
            assert key in data
            assert isinstance(data[key], list)
        
        assert data["current_skills"] == ["Python", "FastAPI"]

def test_profile_analyze_fallback_on_gemini_failure(client):
    """
    Test missing required key in Gemini response triggers fallback analysis path,
    returning HTTP 200 with source='fallback'.
    """
    payload = {
        "user_id": "user_test_002",
        "education": "Bachelor of Technology",
        "degree": "B.Tech",
        "branch": "IT",
        "graduation_year": 2024,
        "target_role": "Backend Engineer",
        "experience_level": "intermediate",
        "skills": ["Python"],
        "interests": ["AI"],
        "projects": ["Project A"],
        "certifications": []
    }

    # Invalid dict missing 'strengths' and 'weaknesses'
    invalid_dict = {
        "current_skills": ["Python"],
        "required_skills": ["Python", "FastAPI"]
    }

    mock_db = MagicMock()

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.profile_service.get_supabase_client", return_value=mock_db):

        mock_gen.return_value = invalid_dict

        response = client.post("/api/profile/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "fallback"
        assert "strengths" in data

def test_profile_analyze_db_insert_failure_returns_500_with_analysis(client, mock_gemini_success_dict):
    """
    Test mocked Supabase insert failure returns 500 but still includes the generated analysis.
    """
    payload = {
        "user_id": "user_test_003",
        "education": "Bachelor of Science",
        "degree": "B.S.",
        "branch": "CS",
        "graduation_year": 2023,
        "target_role": "Backend Engineer",
        "experience_level": "advanced",
        "skills": ["Python", "Django"],
        "interests": ["Backend"],
        "projects": ["Django App"],
        "certifications": []
    }

    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.side_effect = Exception("Supabase DB connection down")

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.profile_service.get_supabase_client", return_value=mock_db):
        
        mock_gen.return_value = mock_gemini_success_dict
        
        response = client.post("/api/profile/analyze", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "database_insert_failed"
        assert "analysis" in data
        assert data["analysis"]["current_skills"] == ["Python", "FastAPI"]
