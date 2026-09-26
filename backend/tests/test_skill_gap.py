import pytest
from unittest.mock import AsyncMock, patch
from app.services.skill_gap_service import SkillGapService

def test_validate_and_rank_gaps_logic():
    """
    Test SkillGapService._validate_and_rank_gaps clamping, normalization, and deterministic sorting.
    """
    service = SkillGapService(gemini_service=None)
    
    raw_gaps = [
        {
            "skill": "Python",
            "current_level": "Intermediate",
            "required_level": "Advanced",
            "gap_score": 35.0,
            "importance": "High",
            "reason": "Backend framework requirement"
        },
        {
            "skill": "Kubernetes",
            "current_level": "None",
            "required_level": "Intermediate",
            "gap_score": 150.0, # test clamping
            "importance": "Critical",
            "reason": "Production cluster orchestration"
        },
        {
            "skill": "Docker",
            "current_level": "Beginner",
            "required_level": "Advanced",
            "gap_score": 75.0,
            "importance": "Critical",
            "reason": "Container setup"
        },
        {
            "skill": "HTML/CSS",
            "current_level": "Beginner",
            "required_level": "Intermediate",
            "gap_score": -10.0, # test clamping lower bound
            "importance": "Low",
            "reason": "Basic frontend knowledge"
        }
    ]

    ranked = service._validate_and_rank_gaps(raw_gaps)
    
    assert len(ranked) == 4
    # Clamping checks
    assert ranked[0].skill == "Kubernetes"
    assert ranked[0].gap_score == 100.0  # clamped from 150
    assert ranked[0].importance == "Critical"
    assert ranked[0].priority == 1
    
    # Critical with score 100 vs score 75
    assert ranked[1].skill == "Docker"
    assert ranked[1].gap_score == 75.0
    assert ranked[1].importance == "Critical"
    assert ranked[1].priority == 2

    # High importance next
    assert ranked[2].skill == "Python"
    assert ranked[2].importance == "High"
    assert ranked[2].priority == 3

    # Low importance last with clamped 0.0
    assert ranked[3].skill == "HTML/CSS"
    assert ranked[3].gap_score == 0.0
    assert ranked[3].importance == "Low"
    assert ranked[3].priority == 4

def test_analyze_skill_gaps_endpoint(client):
    """
    Test POST /api/skills/analyze/{profile_id} endpoint with mock Gemini.
    """
    profile_id = "test_profile_skill_gap_001"
    payload = {
        "target_role": "Backend Software Engineer",
        "skills": ["Python", "SQL", "Git"]
    }

    mock_gemini_gaps = {
        "skill_gaps": [
            {
                "skill": "Python",
                "current_level": "Intermediate",
                "required_level": "Advanced",
                "gap_score": 35.0,
                "importance": "High",
                "reason": "Required for backend core logic development."
            },
            {
                "skill": "Docker",
                "current_level": "None",
                "required_level": "Intermediate",
                "gap_score": 80.0,
                "importance": "Critical",
                "reason": "Containerization required for microservices deployment."
            }
        ]
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_gaps

        response = client.post(f"/api/skills/analyze/{profile_id}", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "profile_id" in data
        assert data["target_role"] == "Backend Software Engineer"
        assert data["total_gaps_identified"] == 2
        
        gaps = data["skill_gaps"]
        assert len(gaps) == 2
        
        # Verify Critical importance ranks priority 1
        assert gaps[0]["skill"] == "Docker"
        assert gaps[0]["priority"] == 1
        assert gaps[0]["importance"] == "Critical"
        assert gaps[0]["gap_score"] == 80.0
        assert gaps[0]["reason"] == "Containerization required for microservices deployment."

        # Verify High importance ranks priority 2
        assert gaps[1]["skill"] == "Python"
        assert gaps[1]["priority"] == 2
        assert gaps[1]["importance"] == "High"
        assert gaps[1]["gap_score"] == 35.0

def test_get_skill_gaps_endpoint(client):
    """
    Test GET /api/skills/gaps/{profile_id} endpoint after running analysis.
    """
    profile_id = "test_profile_skill_gap_002"
    payload = {
        "target_role": "Backend Software Engineer",
        "skills": ["Python"]
    }

    mock_gemini_gaps = {
        "skill_gaps": [
            {
                "skill": "PostgreSQL",
                "current_level": "Beginner",
                "required_level": "Advanced",
                "gap_score": 60.0,
                "importance": "High",
                "reason": "Database query tuning."
            }
        ]
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_gaps
        analyze_res = client.post(f"/api/skills/analyze/{profile_id}", json=payload)
        assert analyze_res.status_code == 200

    get_res = client.get(f"/api/skills/gaps/{profile_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()["data"]
    assert isinstance(fetched_data, list)
    assert len(fetched_data) >= 1
    assert any(item.get("skill") == "PostgreSQL" for item in fetched_data)
