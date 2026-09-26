import pytest

def test_get_dashboard_progress_endpoint(client):
    """
    Test GET /api/progress/{profile_id} returns dashboard-friendly JSON formatted for Recharts.
    """
    profile_id = "test_profile_progress_001"

    response = client.get(f"/api/progress/{profile_id}")
    assert response.status_code == 200
    res_data = response.json()["data"]

    assert res_data["profile_id"] == profile_id
    assert "overall_progress" in res_data
    assert 0 <= res_data["overall_progress"] <= 100

    # Verify skills list
    assert "skills" in res_data
    assert isinstance(res_data["skills"], list)
    if len(res_data["skills"]) > 0:
        s1 = res_data["skills"][0]
        assert "skill" in s1
        assert "progress" in s1
        assert "status" in s1

    # Verify assessment_progress
    assert "assessment_progress" in res_data
    ap = res_data["assessment_progress"]
    assert "average_score" in ap
    assert "recent_scores" in ap

    # Verify interview_progress
    assert "interview_progress" in res_data
    ip = res_data["interview_progress"]
    assert "average_score" in ip
    assert "recent_scores" in ip

    # Verify readiness_history (Recharts line chart format)
    assert "readiness_history" in res_data
    rh = res_data["readiness_history"]
    assert isinstance(rh, list)
    if len(rh) > 0:
        assert "date" in rh[0]
        assert "score" in rh[0]

    # Verify roadmap_progress
    assert "roadmap_progress" in res_data
    rp = res_data["roadmap_progress"]
    assert "completed_tasks" in rp
    assert "total_tasks" in rp
    assert "percentage" in rp

    # Verify completed_activities
    assert "completed_activities" in res_data
    assert isinstance(res_data["completed_activities"], list)

def test_update_progress_and_activity_endpoint(client):
    """
    Test POST /api/progress/{profile_id}/update records updated skills, learning activity, and readiness history.
    """
    profile_id = "test_profile_progress_002"

    update_payload = {
        "skill": "Docker",
        "status": "completed",
        "progress_percentage": 100.0,
        "activity": {
            "type": "task",
            "title": "Completed Docker Security Module"
        },
        "readiness_score": 88.5
    }

    response = client.post(f"/api/progress/{profile_id}/update", json=update_payload)
    assert response.status_code == 200
    res_data = response.json()["data"]

    assert res_data["profile_id"] == profile_id

    # Check updated skill
    docker_skill = next((s for s in res_data["skills"] if s["skill"] == "Docker"), None)
    assert docker_skill is not None
    assert docker_skill["progress"] == 100.0
    assert docker_skill["status"] == "Completed"

    # Check recorded activity
    activities = res_data["completed_activities"]
    latest_act = next((a for a in activities if a["title"] == "Completed Docker Security Module"), None)
    assert latest_act is not None
    assert latest_act["type"] == "task"

    # Check updated readiness history
    history = res_data["readiness_history"]
    latest_rh = history[-1]
    assert latest_rh["score"] == 88.5
