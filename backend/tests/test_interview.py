import pytest
from unittest.mock import AsyncMock, patch

def test_start_interview_flow(client):
    """
    Test POST /api/interview/start initializes server-side session and generates Turn 1 question.
    """
    payload = {
        "target_role": "Backend Engineer",
        "difficulty": "intermediate",
        "num_questions": 3
    }

    mock_gemini_question = {
        "question": "Walk me through how you design asynchronous database access in a FastAPI application."
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_gemini_question

        response = client.post("/api/interview/start", json=payload)
        assert response.status_code == 201
        res_data = response.json()

        assert "interview_id" in res_data
        assert res_data["target_role"] == "Backend Engineer"
        assert res_data["current_turn"] == 1
        assert res_data["total_questions"] == 3
        assert "question" in res_data
        assert res_data["question"] == "Walk me through how you design asynchronous database access in a FastAPI application."

def test_answer_and_next_question_flow(client):
    """
    Test POST /api/interview/{interview_id}/answer evaluates turn answer across 6 criteria
    and returns the next question.
    """
    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = {"question": "Q1: Explain Async Python."}

        start_res = client.post("/api/interview/start", json={"target_role": "Backend Engineer", "num_questions": 3})
        assert start_res.status_code == 201
        interview_id = start_res.json()["interview_id"]

        mock_gemini_eval = {
            "score": 88.0,
            "technical_correctness": 90.0,
            "relevance": 92.0,
            "communication": 85.0,
            "clarity": 85.0,
            "completeness": 85.0,
            "problem_solving_approach": 90.0,
            "feedback": "Excellent async DB handling pattern."
        }
        mock_gemini_next_q = {
            "question": "How do you handle background tasks and worker processes when processing heavy jobs?"
        }
        mock_gemini.side_effect = [mock_gemini_eval, mock_gemini_next_q]

        answer_payload = {
            "user_answer": "I use AsyncSession with SQLAlchemy and asyncpg. I manage connection pooling cleanly and inject DB sessions into FastAPI route dependencies."
        }

        ans_res = client.post(f"/api/interview/{interview_id}/answer", json=answer_payload)
        assert ans_res.status_code == 200
        data = ans_res.json()["data"]

        assert data["interview_id"] == interview_id
        assert data["turn"] == 1
        assert data["has_next_question"] is True
        assert "next_question" in data

        eval_obj = data["evaluation"]
        assert eval_obj["score"] == 88.0
        assert eval_obj["technical_correctness"] == 90.0
        assert eval_obj["relevance"] == 92.0
        assert eval_obj["communication"] == 85.0
        assert eval_obj["clarity"] == 85.0
        assert eval_obj["completeness"] == 85.0
        assert eval_obj["problem_solving_approach"] == 90.0
        assert "feedback" in eval_obj

def test_finish_interview_feedback_structure(client):
    """
    Test POST /api/interview/{interview_id}/finish returns exact feedback structure requested:
    overall_score, technical_score, communication_score, confidence_score, strengths, weaknesses,
    recommendations, and summary.
    """
    mock_start_q = {"question": "Q1: Architecture principles?"}
    mock_eval = {
        "score": 85.0,
        "technical_correctness": 85.0,
        "relevance": 85.0,
        "communication": 85.0,
        "clarity": 85.0,
        "completeness": 85.0,
        "problem_solving_approach": 85.0,
        "feedback": "Good answer."
    }
    mock_next_q = {"question": "Q2: Database tuning?"}
    mock_final_feedback = {
        "overall_score": 85.0,
        "technical_score": 88.0,
        "communication_score": 82.0,
        "confidence_score": 85.0,
        "strengths": ["Strong technical concepts", "Structured problem solving"],
        "weaknesses": ["Minor gaps in edge-case handling"],
        "recommendations": ["Practice failure mode recovery"],
        "summary": "Candidate demonstrated solid backend competencies."
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.side_effect = [mock_start_q, mock_eval, mock_next_q, mock_final_feedback]

        start_res = client.post("/api/interview/start", json={"target_role": "Backend Engineer", "num_questions": 2})
        interview_id = start_res.json()["interview_id"]

        # Answer turn 1
        client.post(f"/api/interview/{interview_id}/answer", json={"user_answer": "Detailed answer for Q1."})

        finish_res = client.post(f"/api/interview/{interview_id}/finish")
        assert finish_res.status_code == 200
        feedback = finish_res.json()["data"]

        # Check required fields
        assert "overall_score" in feedback
        assert "technical_score" in feedback
        assert "communication_score" in feedback
        assert "confidence_score" in feedback
        assert "strengths" in feedback
        assert "weaknesses" in feedback
        assert "recommendations" in feedback
        assert "summary" in feedback
        assert isinstance(feedback["strengths"], list)

def test_get_interview_feedback_endpoint(client):
    """
    Test GET /api/interview/{interview_id}/feedback retrieves completed feedback.
    """
    mock_start_q = {"question": "Q1: Explain PyTorch tensors."}
    mock_eval = {
        "score": 90.0,
        "technical_correctness": 90.0,
        "relevance": 90.0,
        "communication": 90.0,
        "clarity": 90.0,
        "completeness": 90.0,
        "problem_solving_approach": 90.0,
        "feedback": "Great response."
    }
    mock_next_q = {"question": "Q2: Transformer architecture?"}
    mock_final_fb = {
        "overall_score": 90.0,
        "technical_score": 92.0,
        "communication_score": 88.0,
        "confidence_score": 90.0,
        "strengths": ["Deep learning mastery"],
        "weaknesses": ["None"],
        "recommendations": ["Keep practicing"],
        "summary": "Outstanding candidate."
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.side_effect = [mock_start_q, mock_eval, mock_next_q, mock_final_fb]

        start_res = client.post("/api/interview/start", json={"target_role": "AI Engineer", "num_questions": 2})
        interview_id = start_res.json()["interview_id"]

        client.post(f"/api/interview/{interview_id}/answer", json={"user_answer": "I build LLM pipelines using PyTorch and vLLM."})
        client.post(f"/api/interview/{interview_id}/finish")

        fb_res = client.get(f"/api/interview/{interview_id}/feedback")
        assert fb_res.status_code == 200
        feedback = fb_res.json()["data"]

        assert "overall_score" in feedback
        assert "summary" in feedback

def test_interrupted_interview_session_graceful_finish(client):
    """
    Test that an interrupted session (finishing early without completing all turns)
    is handled gracefully and synthesizes feedback for turns completed so far.
    """
    mock_start_q = {"question": "Q1: Explain CI/CD pipelines."}
    mock_eval = {
        "score": 80.0,
        "technical_correctness": 80.0,
        "relevance": 80.0,
        "communication": 80.0,
        "clarity": 80.0,
        "completeness": 80.0,
        "problem_solving_approach": 80.0,
        "feedback": "Good answer."
    }
    mock_next_q = {"question": "Q2: Kubernetes ingress?"}
    mock_final_fb = {
        "overall_score": 80.0,
        "technical_score": 80.0,
        "communication_score": 80.0,
        "confidence_score": 80.0,
        "strengths": ["DevOps fundamentals"],
        "weaknesses": ["Interrupted session"],
        "recommendations": ["Complete full session"],
        "summary": "Interrupted session feedback synthesized."
    }

    with patch("app.services.gemini_service.GeminiService.generate_structured", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.side_effect = [mock_start_q, mock_eval, mock_next_q, mock_final_fb]

        start_res = client.post("/api/interview/start", json={"target_role": "DevOps Engineer", "num_questions": 5})
        interview_id = start_res.json()["interview_id"]

        # Answer only 1 of 5 questions then finish prematurely
        client.post(f"/api/interview/{interview_id}/answer", json={"user_answer": "I configure CI/CD pipelines using GitHub Actions and Terraform."})

        finish_res = client.post(f"/api/interview/{interview_id}/finish")
        assert finish_res.status_code == 200
        feedback = finish_res.json()["data"]

        assert "overall_score" in feedback
        assert feedback["overall_score"] > 0
        assert "summary" in feedback
