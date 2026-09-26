import pytest
from unittest.mock import AsyncMock, patch

def test_generate_personalized_roadmap_endpoint(client):
    """
    Test POST /api/roadmap/generate/{profile_id} generates personalized roadmap using student skill gaps.
    """
    profile_id = "test_profile_roadmap_001"
    payload = {
        "target_role": "Backend Engineer",
        "current_skills": ["Python", "Git"],
        "skill_gaps": ["Docker", "FastAPI", "PostgreSQL"],
        "priority_skills": ["Docker", "FastAPI"],
        "experience_level": "Entry-level",
        "available_learning_time": "12 hours/week",
        "duration_weeks": 8
    }

    mock_gemini_roadmap = {
        "duration_weeks": 8,
        "target_role": "Backend Engineer",
        "weeks": [
            {
                "week": 1,
                "focus": "Docker Containerization Fundamentals",
                "skills": ["Docker"],
                "topics": ["Containerization", "Dockerfiles", "Docker Compose"],
                "tasks": ["Install Docker", "Create containerized FastAPI app"],
                "mini_project": "Dockerized REST API",
                "expected_outcome": "Functional containerized application"
            },
            {
                "week": 2,
                "focus": "FastAPI Mechanics & Routing",
                "skills": ["FastAPI"],
                "topics": ["Path operations", "Pydantic validation", "Dependency Injection"],
                "tasks": ["Build CRUD endpoints", "Implement middleware"],
                "mini_project": "Async User Management Service",
                "expected_outcome": "Clean API service with OpenAPI docs"
            },
            {
                "week": 3,
                "focus": "PostgreSQL & Database Design",
                "skills": ["PostgreSQL"],
                "topics": ["Schema design", "SQL Queries", "ORM Integration"],
                "tasks": ["Design relational schema", "Write query optimizations"],
                "mini_project": "Database persistence layer",
                "expected_outcome": "Normalized PostgreSQL DB integration"
            },
            {
                "week": 4,
                "focus": "Integration & System Architecture",
                "skills": ["Docker", "FastAPI", "PostgreSQL"],
                "topics": ["Microservices interaction", "Environment config", "Security"],
                "tasks": ["Connect FastAPI to PostgreSQL container", "Run migrations"],
                "mini_project": "End-to-end Backend System",
                "expected_outcome": "Fully dockerized multi-container app"
            },
            {
                "week": 5,
                "focus": "Testing & QA Automation",
                "skills": ["Python", "FastAPI"],
                "topics": ["pytest", "TestClient", "Mocking"],
                "tasks": ["Write unit tests", "Achieve 80%+ test coverage"],
                "mini_project": "Automated Test Suite",
                "expected_outcome": "Passing CI test execution"
            },
            {
                "week": 6,
                "focus": "Performance & Caching",
                "skills": ["PostgreSQL", "FastAPI"],
                "topics": ["Redis caching", "Query indexing", "Async execution"],
                "tasks": ["Implement response caching", "Profile DB queries"],
                "mini_project": "Cached API Service",
                "expected_outcome": "Reduced response latency under load"
            },
            {
                "week": 7,
                "focus": "Security & Authentication",
                "skills": ["FastAPI", "Python"],
                "topics": ["JWT Auth", "OAuth2", "Password Hashing"],
                "tasks": ["Implement JWT middleware", "Secure API routes"],
                "mini_project": "Auth Microservice",
                "expected_outcome": "Role-based access controlled API"
            },
            {
                "week": 8,
                "focus": "Production Deployment & Capstone",
                "skills": ["Docker", "FastAPI", "PostgreSQL"],
                "topics": ["CI/CD pipelines", "Production logging", "Cloud hosting"],
                "tasks": ["Deploy to cloud platform", "Configure monitoring"],
                "mini_project": "Production Backend Capstone",
                "expected_outcome": "Live deployed backend portfolio project"
            }
        ]
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_roadmap

        response = client.post(f"/api/roadmap/generate/{profile_id}", json=payload)
        assert response.status_code == 200
        res_data = response.json()

        assert res_data["profile_id"] == profile_id
        assert res_data["target_role"] == "Backend Engineer"
        assert res_data["duration_weeks"] == 8

        roadmap = res_data["data"]["roadmap_data"]
        assert roadmap["duration_weeks"] == 8
        assert len(roadmap["weeks"]) == 8

        # Check required fields for week 1
        w1 = roadmap["weeks"][0]
        assert w1["week"] == 1
        assert "focus" in w1
        assert "skills" in w1
        assert "topics" in w1
        assert "tasks" in w1
        assert "mini_project" in w1
        assert "expected_outcome" in w1
        assert "Docker" in w1["skills"]

def test_get_roadmap_endpoint(client):
    """
    Test GET /api/roadmap/{profile_id} retrieves generated roadmap.
    """
    profile_id = "test_profile_roadmap_002"
    payload = {
        "target_role": "Fullstack Developer",
        "skill_gaps": ["React", "TypeScript"],
        "duration_weeks": 4
    }

    gen_res = client.post(f"/api/roadmap/generate/{profile_id}", json=payload)
    assert gen_res.status_code == 200

    get_res = client.get(f"/api/roadmap/{profile_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()

    assert fetched_data["profile_id"] == profile_id
    assert fetched_data["target_role"] == "Fullstack Developer"
    assert "data" in fetched_data
    assert "roadmap_data" in fetched_data["data"]
    assert len(fetched_data["data"]["roadmap_data"]["weeks"]) == 4

def test_get_roadmap_not_found_endpoint(client):
    """
    Test GET /api/roadmap/{profile_id} returns 404 if no roadmap exists.
    """
    response = client.get("/api/roadmap/non_existent_profile_999999")
    assert response.status_code == 404
    assert "No learning roadmap found" in response.json()["detail"]

def test_roadmap_regeneration_on_role_change(client):
    """
    Test POST /api/roadmap/generate/{profile_id} overwrites existing roadmap on profile/role update.
    """
    profile_id = "test_profile_roadmap_003"
    
    # 1. Initial generation for Backend Developer
    payload_1 = {
        "target_role": "Backend Developer",
        "skill_gaps": ["Python", "SQL"],
        "duration_weeks": 4
    }
    client.post(f"/api/roadmap/generate/{profile_id}", json=payload_1)

    # 2. Regeneration for AI/ML Engineer
    payload_2 = {
        "target_role": "AI/ML Engineer",
        "skill_gaps": ["PyTorch", "Transformers", "CUDA"],
        "duration_weeks": 6
    }
    regen_res = client.post(f"/api/roadmap/generate/{profile_id}", json=payload_2)
    assert regen_res.status_code == 200

    # 3. Retrieve latest roadmap
    get_res = client.get(f"/api/roadmap/{profile_id}")
    assert get_res.status_code == 200
    res_data = get_res.json()

    assert res_data["target_role"] == "AI/ML Engineer"
    assert res_data["duration_weeks"] == 6
    assert len(res_data["data"]["roadmap_data"]["weeks"]) == 6
