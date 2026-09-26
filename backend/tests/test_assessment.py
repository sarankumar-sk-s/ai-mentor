import pytest
from unittest.mock import AsyncMock, patch

def test_generate_assessment_endpoint_hides_correct_answers(client):
    """
    Test POST /api/assessment/generate generates structured questions (MCQ, coding, conceptual)
    and verifies correct_answer is stripped prior to submission.
    """
    payload = {
        "target_role": "Backend Engineer",
        "selected_topic": "FastAPI & Async Python",
        "difficulty": "intermediate",
        "num_questions": 3,
        "skill_gaps": ["Docker", "FastAPI"]
    }

    mock_gemini_questions = {
        "questions": [
            {
                "question_id": "q1",
                "question": "Which HTTP method is idempotent?",
                "type": "mcq",
                "options": ["GET", "POST", "PATCH", "DELETE"],
                "correct_answer": "GET",
                "difficulty": "intermediate",
                "skill": "FastAPI"
            },
            {
                "question_id": "q2",
                "question": "Write a FastAPI route handling POST request with Pydantic validation.",
                "type": "coding",
                "options": [],
                "correct_answer": "@app.post('/items') async def create(item: Item): return item",
                "difficulty": "intermediate",
                "skill": "FastAPI"
            },
            {
                "question_id": "q3",
                "question": "Explain container isolation in Docker.",
                "type": "conceptual",
                "options": [],
                "correct_answer": "Docker uses Linux namespaces and cgroups for process isolation.",
                "difficulty": "intermediate",
                "skill": "Docker"
            }
        ]
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_questions

        response = client.post("/api/assessment/generate", json=payload)
        assert response.status_code == 201
        res_data = response.json()

        assert "assessment_id" in res_data
        assessment_id = res_data["assessment_id"]
        questions = res_data["data"]["questions"]

        assert len(questions) == 3

        # SECURITY RULE: Never expose correct_answer before submission!
        for q in questions:
            assert "question_id" in q
            assert "question" in q
            assert "type" in q
            assert "difficulty" in q
            assert "skill" in q
            assert "correct_answer" not in q, f"Security violation: correct_answer exposed in unsubmitted question {q['question_id']}"

def test_get_unsubmitted_assessment_hides_correct_answers(client):
    """
    Test GET /api/assessment/{assessment_id} hides correct_answer when status is pending/unsubmitted.
    """
    gen_payload = {
        "target_role": "Software Engineer",
        "selected_topic": "General Engineering",
        "num_questions": 2
    }
    gen_res = client.post("/api/assessment/generate", json=gen_payload)
    assert gen_res.status_code == 201
    assessment_id = gen_res.json()["assessment_id"]

    get_res = client.get(f"/api/assessment/{assessment_id}")
    assert get_res.status_code == 200
    record = get_res.json()["data"]

    assert record["status"] == "pending"
    for q in record["questions"]:
        assert "correct_answer" not in q

def test_submit_assessment_evaluation(client):
    """
    Test POST /api/assessment/{assessment_id}/submit validates answers, calculates scores,
    runs qualitative/deterministic evaluation, and returns weak areas.
    """
    gen_payload = {
        "target_role": "Backend Developer",
        "selected_topic": "Python Fundamentals",
        "num_questions": 3,
        "skill_gaps": ["Python", "SQL"]
    }
    gen_res = client.post("/api/assessment/generate", json=gen_payload)
    assert gen_res.status_code == 201
    assessment_id = gen_res.json()["assessment_id"]

    # Submit answers
    submit_payload = {
        "answers": [
            {
                "question_id": "q_1",
                "user_answer": "Optimizing efficiency and reliability of Python"
            },
            {
                "question_id": "q_2",
                "user_answer": "Balancing performance, memory footprint, and maintainability in Python applications."
            },
            {
                "question_id": "q_3",
                "user_answer": "def process(): pass"
            }
        ]
    }

    sub_res = client.post(f"/api/assessment/{assessment_id}/submit", json=submit_payload)
    assert sub_res.status_code == 200
    res_data = sub_res.json()

    assert res_data["assessment_id"] == assessment_id
    assert "overall_score" in res_data
    eval_data = res_data["data"]

    assert "overall_score" in eval_data
    assert "weak_areas" in eval_data
    assert "overall_feedback" in eval_data
    assert len(eval_data["question_evaluations"]) == 3

def test_get_assessment_result_after_submission(client):
    """
    Test GET /api/assessment/{assessment_id}/result returns full evaluated result with correct answers.
    """
    gen_payload = {
        "target_role": "DevOps Engineer",
        "selected_topic": "Docker",
        "num_questions": 2
    }
    gen_res = client.post("/api/assessment/generate", json=gen_payload)
    assessment_id = gen_res.json()["assessment_id"]

    # Submit answers
    submit_payload = {
        "answers": [
            {"question_id": "q_1", "user_answer": "Containerization option"},
            {"question_id": "q_2", "user_answer": "Detailed answer for conceptual question"}
        ]
    }
    client.post(f"/api/assessment/{assessment_id}/submit", json=submit_payload)

    result_res = client.get(f"/api/assessment/{assessment_id}/result")
    assert result_res.status_code == 200
    result = result_res.json()["data"]

    assert result["assessment_id"] == assessment_id
    assert "question_evaluations" in result
    assert len(result["question_evaluations"]) == 2

    # After submission, question evaluations include correct_answer and feedback
    for q_eval in result["question_evaluations"]:
        assert "correct_answer" in q_eval
        assert "user_answer" in q_eval
        assert "is_correct" in q_eval
        assert "score" in q_eval
        assert "feedback" in q_eval

def test_get_assessment_result_unsubmitted_fails(client):
    """
    Test GET /api/assessment/{assessment_id}/result returns 400 Bad Request if assessment is unsubmitted.
    """
    gen_payload = {"num_questions": 1}
    gen_res = client.post("/api/assessment/generate", json=gen_payload)
    assessment_id = gen_res.json()["assessment_id"]

    result_res = client.get(f"/api/assessment/{assessment_id}/result")
    assert result_res.status_code == 400
    assert "has not been submitted yet" in result_res.json()["detail"]
