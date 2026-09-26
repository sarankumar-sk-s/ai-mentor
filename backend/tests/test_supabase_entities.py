def test_skill_gap_endpoints(client):
    create_payload = {
        "profile_id": "prof-123",
        "skill": "System Design",
        "current_level": "Beginner",
        "required_level": "Advanced",
        "gap_score": 70.0,
        "importance": "high"
    }
    res = client.post("/api/skill-gaps", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    get_res = client.get(f"/api/skill-gaps/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["skill"] == "System Design"

    list_res = client.get("/api/skill-gaps/profile/prof-123")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

def test_roadmap_endpoints(client):
    create_payload = {
        "profile_id": "prof-123",
        "roadmap_data": {"weeks": [{"week": 1, "topic": "PostgreSQL & FastAPI"}]},
        "duration_weeks": 6
    }
    res = client.post("/api/roadmaps", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    get_res = client.get(f"/api/roadmaps/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["duration_weeks"] == 6

def test_assessment_endpoints(client):
    create_payload = {
        "profile_id": "prof-123",
        "assessment_type": "technical",
        "questions": [{"id": 1, "text": "What is dependency injection in FastAPI?"}],
        "answers": [{"id": 1, "answer": "Using Depends()"}],
        "score": 90.0,
        "feedback": "Great understanding of FastAPI dependencies."
    }
    res = client.post("/api/assessments", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    get_res = client.get(f"/api/assessments/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["score"] == 90.0

def test_interview_endpoints(client):
    create_payload = {
        "profile_id": "prof-123",
        "role": "Backend Engineer",
        "questions": ["Explain ACID properties in PostgreSQL."],
        "answers": ["Atomicity, Consistency, Isolation, Durability."],
        "feedback": {"strengths": ["Clear DB fundamentals"]},
        "overall_score": 88.5
    }
    res = client.post("/api/interviews", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    get_res = client.get(f"/api/interviews/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["overall_score"] == 88.5

def test_readiness_score_endpoints(client):
    valid_uuid = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    create_payload = {
        "profile_id": valid_uuid,
        "technical_score": 85.0,
        "skill_coverage_score": 80.0,
        "project_score": 90.0,
        "assessment_score": 75.0,
        "interview_score": 88.0,
        "overall_score": 83.75,
        "summary": "High technical readiness with strong problem solving.",
        "improvement_priorities": ["Learn Docker"]
    }
    res = client.post("/api/readiness", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    get_res = client.get(f"/api/readiness/{record_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["overall_score"] == 83.75

    latest_res = client.get(f"/api/readiness/profile/{valid_uuid}/latest")
    assert latest_res.status_code == 200



def test_progress_endpoints(client):
    create_payload = {
        "profile_id": "prof-123",
        "skill": "FastAPI",
        "status": "in_progress",
        "progress_percentage": 50.0
    }
    res = client.post("/api/progress", json=create_payload)
    assert res.status_code == 201
    record_id = res.json()["data"]["id"]

    update_payload = {"progress_percentage": 75.0, "status": "in_progress"}
    put_res = client.put(f"/api/progress/{record_id}", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["data"]["progress_percentage"] == 75.0
