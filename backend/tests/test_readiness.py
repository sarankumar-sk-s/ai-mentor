import pytest
from unittest.mock import MagicMock, AsyncMock, patch

def test_calculate_readiness_score_endpoint(client):
    """
    Test POST /api/readiness/calculate calculates sub-scores, synthesizes Gemini summary,
    and returns 200 with complete response schema.
    """
    payload = {
        "profile_id": "test_profile_readiness_001",
        "target_role": "Backend Software Engineer",
        "experience_level": "beginner",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
        "projects": ["PrepPilot AI Mentor", "E-commerce API"],
        "certifications": ["AWS Certified Developer"]
    }

    mock_gemini_qualitative = {
        "summary": "Candidate exhibits strong readiness for Backend Software Engineer role.",
        "improvement_priorities": [
            "Learn containerization using Docker.",
            "Study database indexing and query performance."
        ]
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_qualitative
        
        response = client.post("/api/readiness/calculate", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["profile_id"] is not None
        assert "overall_score" in data
        assert "technical_score" in data
        assert "skill_coverage_score" in data
        assert "project_score" in data
        assert "assessment_score" in data
        assert "interview_score" in data
        assert data["summary"] == mock_gemini_qualitative["summary"]
        assert len(data["improvement_priorities"]) == 2

def test_get_readiness_by_profile_id_endpoint(client):
    """
    Test GET /api/readiness/{profile_id} retrieves calculated score.
    """
    payload = {
        "profile_id": "test_profile_readiness_002",
        "target_role": "Backend Engineer",
        "skills": ["Python", "FastAPI"],
        "projects": ["API Service"],
        "certifications": []
    }

    calc_res = client.post("/api/readiness/calculate", json=payload)
    assert calc_res.status_code == 200

    get_res = client.get("/api/readiness/test_profile_readiness_002")
    assert get_res.status_code == 200
    fetched_data = get_res.json()["data"]
    assert "overall_score" in fetched_data
