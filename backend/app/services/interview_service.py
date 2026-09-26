import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.database import get_supabase_client
from app.schemas.interview import (
    InterviewStartRequestSchema,
    InterviewAnswerRequestSchema,
    InterviewCreateSchema,
    InterviewUpdateSchema
)
from app.services.gemini_service import GeminiService
from app.services.profile_service import ProfileService
from app.services.skill_gap_service import SkillGapService

logger = logging.getLogger(__name__)

_in_memory_interviews: Dict[str, Dict[str, Any]] = {}

QUESTION_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"}
    },
    "required": ["question"]
}

TURN_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "technical_correctness": {"type": "number"},
        "relevance": {"type": "number"},
        "communication": {"type": "number"},
        "clarity": {"type": "number"},
        "completeness": {"type": "number"},
        "problem_solving_approach": {"type": "number"},
        "feedback": {"type": "string"}
    },
    "required": [
        "score", "technical_correctness", "relevance",
        "communication", "clarity", "completeness",
        "problem_solving_approach", "feedback"
    ]
}

FINAL_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number"},
        "technical_score": {"type": "number"},
        "communication_score": {"type": "number"},
        "confidence_score": {"type": "number"},
        "strengths": {
            "type": "array",
            "items": {"type": "string"}
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"}
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"}
        },
        "summary": {"type": "string"}
    },
    "required": [
        "overall_score", "technical_score", "communication_score",
        "confidence_score", "strengths", "weaknesses",
        "recommendations", "summary"
    ]
}

def _generate_fallback_question(
    target_role: str,
    turn_num: int,
    skill_gaps: List[str]
) -> str:
    gaps = skill_gaps or ["System Architecture", "Async Execution", "Database Tuning", "Error Recovery"]
    gap = gaps[(turn_num - 1) % len(gaps)]

    fallback_questions = [
        f"Can you explain your experience with {gap} when building scalable applications for a {target_role} role?",
        f"Describe how you would design and optimize a high-throughput backend component addressing {gap}.",
        f"Walk me through a production issue or bug related to {gap} that you diagnosed and resolved.",
        f"How do you ensure clean code, comprehensive testing, and observability when implementing {gap}?",
        f"If you were asked to mentor a junior engineer on {gap}, what key architectural principles would you emphasize?"
    ]
    return fallback_questions[(turn_num - 1) % len(fallback_questions)]

def _evaluate_fallback_answer(
    question: str,
    user_answer: str,
    target_role: str
) -> Dict[str, Any]:
    ans = user_answer.strip()
    ans_len = len(ans)

    if not ans:
        return {
            "score": 0.0,
            "technical_correctness": 0.0,
            "relevance": 0.0,
            "communication": 0.0,
            "clarity": 0.0,
            "completeness": 0.0,
            "problem_solving_approach": 0.0,
            "feedback": "No answer provided by candidate.",
            "source": "fallback"
        }

    tech_corr = min(100.0, max(50.0, ans_len * 0.4))
    relevance = min(100.0, 70.0 + (10.0 if any(k in ans.lower() for k in ["design", "system", "code", "data", "api"]) else 0.0))
    comm = min(100.0, max(60.0, ans_len * 0.35))
    clarity = min(100.0, 75.0 if "." in ans else 60.0)
    comp = min(100.0, max(55.0, ans_len * 0.3))
    ps_approach = min(100.0, 80.0 if any(k in ans.lower() for k in ["because", "first", "solution", "result"]) else 65.0)

    overall = round((tech_corr + relevance + comm + clarity + comp + ps_approach) / 6.0, 1)

    return {
        "score": overall,
        "technical_correctness": round(tech_corr, 1),
        "relevance": round(relevance, 1),
        "communication": round(comm, 1),
        "clarity": round(clarity, 1),
        "completeness": round(comp, 1),
        "problem_solving_approach": round(ps_approach, 1),
        "feedback": f"Demonstrated structured response for {target_role}. Keep expanding on specific technical implementation details.",
        "source": "fallback"
    }

def _generate_fallback_final_feedback(
    turns: List[Dict[str, Any]],
    target_role: str
) -> Dict[str, Any]:
    completed_turns = [t for t in turns if t.get("user_answer") and t.get("evaluation")]
    if not completed_turns:
        return {
            "overall_score": 0.0,
            "technical_score": 0.0,
            "communication_score": 0.0,
            "confidence_score": 0.0,
            "strengths": ["Session initiated"],
            "weaknesses": ["No interview turns completed before finishing"],
            "recommendations": ["Complete mock interview turns to receive detailed AI evaluation"],
            "summary": f"Mock interview session for {target_role} was ended without completing response turns.",
            "source": "fallback"
        }

    tech_scores = [(t.get("evaluation") or {}).get("technical_correctness", 70.0) for t in completed_turns]
    comm_scores = [(t.get("evaluation") or {}).get("communication", 70.0) for t in completed_turns]
    overall_scores = [(t.get("evaluation") or {}).get("score", 70.0) for t in completed_turns]

    avg_tech = round(sum(tech_scores) / len(tech_scores), 1)
    avg_comm = round(sum(comm_scores) / len(comm_scores), 1)
    avg_overall = round(sum(overall_scores) / len(overall_scores), 1)
    avg_conf = round((avg_tech + avg_comm) / 2.0, 1)

    return {
        "overall_score": avg_overall,
        "technical_score": avg_tech,
        "communication_score": avg_comm,
        "confidence_score": avg_conf,
        "strengths": [
            f"Demonstrated clear technical intent for {target_role}",
            "Structured responses with relevant problem-solving approaches"
        ],
        "weaknesses": [
            "Could elaborate further on production edge cases and system resilience"
        ],
        "recommendations": [
            "Practice explaining architectural trade-offs using STAR method",
            "Review core technical concepts and memory/performance optimizations"
        ],
        "summary": f"Candidate completed {len(completed_turns)} interview turns for {target_role} with an overall score of {avg_overall}/100.",
        "source": "fallback"
    }

class InterviewService:
    """
    Repository & Service layer managing AI-powered mock interview sessions,
    server-side conversation state, per-turn evaluation, and final feedback synthesis.
    """
    def __init__(
        self,
        gemini_service: Optional[GeminiService] = None,
        profile_service: Optional[ProfileService] = None,
        skill_gap_service: Optional[SkillGapService] = None
    ):
        self.db = get_supabase_client()
        self.gemini_service = gemini_service or GeminiService()
        self.profile_service = profile_service or ProfileService(gemini_service=self.gemini_service)
        self.skill_gap_service = skill_gap_service or SkillGapService(gemini_service=self.gemini_service)

    async def start_interview(
        self,
        request_data: InterviewStartRequestSchema
    ) -> Dict[str, Any]:
        profile_id = request_data.profile_id
        target_role = request_data.target_role or "Software Engineer"
        difficulty = request_data.difficulty or "intermediate"
        num_questions = request_data.num_questions or 5
        skill_gaps = []

        if profile_id:
            profile_record = await self.profile_service.get_profile_by_id(profile_id)
            if profile_record:
                target_role = request_data.target_role or profile_record.get("target_role") or target_role
                gap_records = await self.skill_gap_service.list_by_profile_id(profile_id)
                skill_gaps = [g.get("skill") for g in gap_records if g.get("skill")] or profile_record.get("analysis", {}).get("skill_gaps") or []

        question_1 = None
        q1_source = "fallback"

        if self.gemini_service and self.gemini_service.is_configured():
            prompt = f"""
            You are a senior technical hiring manager conducting a realistic mock interview for a '{target_role}' candidate.

            Candidate Profile:
            - Target Role: {target_role}
            - Difficulty Level: {difficulty}
            - Identified Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'Core engineering fundamentals'}

            Generate Turn 1: Open the interview with an engaging, realistic technical question tailored to '{target_role}' that tests their problem-solving and architectural understanding.

            Return JSON matching the schema with key 'question'.
            """
            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=QUESTION_GENERATION_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and ai_res.get("question"):
                    question_1 = ai_res["question"]
                    q1_source = ai_res.get("source", "gemini")
            except Exception as exc:
                logger.warning(f"Gemini first interview question generation failed: {exc}")

        if not question_1:
            question_1 = _generate_fallback_question(target_role, 1, skill_gaps)
            q1_source = "fallback"

        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())

        record = {
            "id": record_id,
            "profile_id": profile_id,
            "role": target_role,
            "difficulty": difficulty,
            "status": "in_progress",
            "current_turn": 1,
            "num_questions": num_questions,
            "source": q1_source,
            "turns": [
                {
                    "turn": 1,
                    "question": question_1,
                    "user_answer": None,
                    "evaluation": None
                }
            ],
            "questions": [question_1],
            "answers": [],
            "feedback": {},
            "overall_score": 0.0,
            "created_at": now,
            "updated_at": now
        }

        # Save to Supabase using standard schema columns
        if self.db is not None:
            db_payload = {
                "id": record_id,
                "profile_id": profile_id,
                "role": target_role,
                "questions": [question_1],
                "answers": [],
                "feedback": {},
                "overall_score": 0.0,
                "created_at": now
            }
            try:
                self.db.table("interviews").insert(db_payload).execute()
                logger.info(f"Inserted interview session {record_id} into Supabase")
            except Exception as db_err:
                logger.warning(f"Supabase insert failed for interview {record_id}: {db_err}")

        _in_memory_interviews[record_id] = record
        return record

    async def submit_answer(
        self,
        record_id: str,
        answer_data: InterviewAnswerRequestSchema
    ) -> Dict[str, Any]:
        record = await self.get_by_id(record_id)
        if not record:
            raise ValueError(f"Interview session '{record_id}' not found.")

        if record.get("status") == "completed":
            raise ValueError(f"Interview session '{record_id}' has already been completed.")

        turns = record.get("turns", [])
        current_turn_idx = record.get("current_turn", 1) - 1

        if current_turn_idx < 0 or current_turn_idx >= len(turns):
            raise ValueError(f"Invalid turn state for interview session '{record_id}'.")

        turn_obj = turns[current_turn_idx]
        current_q = turn_obj.get("question", "")
        user_ans = answer_data.user_answer
        target_role = record.get("role", "Software Engineer")
        num_questions = record.get("num_questions", 5)

        eval_result = None
        if self.gemini_service and self.gemini_service.is_configured():
            prompt = f"""
            You are a technical interviewer evaluating a candidate's response in a mock interview.

            Interview Context:
            - Role: {target_role}
            - Question Asked: {current_q}
            - Candidate Answer: {user_ans}

            Evaluate the candidate's response strictly across ALL 6 required criteria (each rated from 0.0 to 100.0):
            1. technical_correctness: Accuracy of technical concepts
            2. relevance: Directness and alignment with the question
            3. communication: Flow, structure, and articulation
            4. clarity: Conciseness and clear phrasing
            5. completeness: Thoroughness of solution
            6. problem_solving_approach: Structured reasoning & methodology

            Calculate overall 'score' as the average of these 6 subscores. Provide concise, actionable 'feedback'.
            Return strictly valid JSON conforming to the schema.
            """
            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=TURN_EVALUATION_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and "score" in ai_res:
                    eval_result = ai_res
                    if "source" not in eval_result:
                        eval_result["source"] = "gemini"
            except Exception as exc:
                logger.warning(f"Gemini turn evaluation failed: {exc}")

        if not eval_result:
            eval_result = _evaluate_fallback_answer(current_q, user_ans, target_role)
            eval_result["source"] = "fallback"

        turn_obj["user_answer"] = user_ans
        turn_obj["evaluation"] = eval_result

        questions_list = record.get("questions", [])
        answers_list = [t.get("user_answer") for t in turns if t.get("user_answer")]

        next_q = None
        has_next = False
        next_turn_num = current_turn_idx + 2

        if next_turn_num <= num_questions:
            has_next = True
            history_text = "\n".join([
                f"Turn {t['turn']} Q: {t['question']}\nCandidate A: {t.get('user_answer', 'None')}"
                for t in turns
            ])

            if self.gemini_service and self.gemini_service.is_configured():
                next_prompt = f"""
                You are a senior technical interviewer conducting a mock interview for '{target_role}'.

                Interview Conversation History:
                {history_text}

                Generate Turn {next_turn_num} question:
                Ask a follow-up or next technical question that logically builds upon previous answers, tests deeper technical knowledge, or explores a new relevant skill area for {target_role}.

                Return JSON matching schema with key 'question'.
                """
                try:
                    next_res = await self.gemini_service.generate_structured(
                        prompt=next_prompt,
                        schema=QUESTION_GENERATION_SCHEMA,
                        model="gemini-3.1-flash-lite"
                    )
                    if isinstance(next_res, dict) and next_res.get("question"):
                        next_q = next_res["question"]
                except Exception as exc:
                    logger.warning(f"Gemini next question generation failed: {exc}")

            if not next_q:
                next_q = _generate_fallback_question(target_role, next_turn_num, [])

            turns.append({
                "turn": next_turn_num,
                "question": next_q,
                "user_answer": None,
                "evaluation": None
            })
            questions_list.append(next_q)
            record["current_turn"] = next_turn_num

        now = datetime.now(timezone.utc).isoformat()
        record["turns"] = turns
        record["questions"] = questions_list
        record["answers"] = answers_list
        record["updated_at"] = now

        # Update Supabase using standard schema columns
        if self.db is not None:
            db_update = {
                "questions": questions_list,
                "answers": answers_list
            }
            try:
                self.db.table("interviews").update(db_update).eq("id", record_id).execute()
            except Exception as e:
                logger.warning(f"Supabase update failed for interview answer {record_id}: {e}")

        _in_memory_interviews[record_id] = record

        return {
            "interview_id": record_id,
            "turn": current_turn_idx + 1,
            "evaluation": eval_result,
            "has_next_question": has_next,
            "next_question": next_q,
            "source": eval_result.get("source", "gemini")
        }

    async def get_next_question(self, record_id: str) -> Dict[str, Any]:
        record = await self.get_by_id(record_id)
        if not record:
            raise ValueError(f"Interview session '{record_id}' not found.")

        turns = record.get("turns", [])
        current_turn = record.get("current_turn", 1)

        if not turns:
            raise ValueError(f"No turns found for interview session '{record_id}'.")

        turn_obj = turns[min(current_turn - 1, len(turns) - 1)]

        return {
            "interview_id": record_id,
            "current_turn": current_turn,
            "total_questions": record.get("num_questions", 5),
            "status": record.get("status", "in_progress"),
            "question": turn_obj.get("question"),
            "source": record.get("source", "gemini")
        }

    async def finish_interview(self, record_id: str) -> Dict[str, Any]:
        record = await self.get_by_id(record_id)
        if not record:
            raise ValueError(f"Interview session '{record_id}' not found.")

        target_role = record.get("role", "Software Engineer")
        turns = record.get("turns", [])
        completed_turns = [t for t in turns if t.get("user_answer") and t.get("evaluation")]

        history_lines = []
        for t in turns:
            t_eval = t.get("evaluation") or {}
            score_val = t_eval.get("score", 0)
            fb_val = t_eval.get("feedback", "")
            history_lines.append(
                f"Turn {t.get('turn')} Q: {t.get('question')}\n"
                f"Candidate Answer: {t.get('user_answer', 'Not answered')}\n"
                f"Turn Score: {score_val} | Feedback: {fb_val}"
            )
        history_summary = "\n".join(history_lines)

        final_feedback = None

        if self.gemini_service and self.gemini_service.is_configured() and completed_turns:
            prompt = f"""
            You are a principal technical hiring manager synthesizing final candidate feedback for a mock interview.

            Role: {target_role}
            Completed Interview Trajectory ({len(completed_turns)} turns):
            {history_summary}

            Synthesize a comprehensive final evaluation. Provide strictly valid JSON with EXACTLY these fields:
            - overall_score: (float 0-100)
            - technical_score: (float 0-100)
            - communication_score: (float 0-100)
            - confidence_score: (float 0-100)
            - strengths: (array of strings) key technical and communication strengths
            - weaknesses: (array of strings) identified areas needing improvement
            - recommendations: (array of strings) concrete, actionable preparation advice
            - summary: (string) overall qualitative executive summary of candidate readiness
            """

            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=FINAL_FEEDBACK_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and "overall_score" in ai_res:
                    final_feedback = ai_res
                    if "source" not in final_feedback:
                        final_feedback["source"] = "gemini"
            except Exception as exc:
                logger.warning(f"Gemini final feedback synthesis failed: {exc}")

        if not final_feedback:
            final_feedback = _generate_fallback_final_feedback(turns, target_role)
            final_feedback["source"] = "fallback"

        now = datetime.now(timezone.utc).isoformat()
        overall_score = float(final_feedback.get("overall_score", 0.0))

        record["status"] = "completed"
        record["feedback"] = final_feedback
        record["overall_score"] = overall_score
        record["updated_at"] = now

        if self.db is not None:
            db_update = {
                "feedback": final_feedback,
                "overall_score": overall_score
            }
            try:
                self.db.table("interviews").update(db_update).eq("id", record_id).execute()
            except Exception as e:
                logger.warning(f"Supabase update failed for finish interview {record_id}: {e}")

        _in_memory_interviews[record_id] = record
        return final_feedback

    async def get_interview_feedback(self, record_id: str) -> Dict[str, Any]:
        record = await self.get_by_id(record_id)
        if not record:
            raise ValueError(f"Interview session '{record_id}' not found.")

        existing_feedback = record.get("feedback")
        if existing_feedback and isinstance(existing_feedback, dict) and "overall_score" in existing_feedback and existing_feedback.get("overall_score", 0) > 0:
            return existing_feedback

        return await self.finish_interview(record_id)

    async def create_interview(self, data: InterviewCreateSchema) -> Dict[str, Any]:
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": data.profile_id,
            "role": data.role,
            "questions": data.questions,
            "answers": data.answers,
            "feedback": data.feedback,
            "overall_score": data.overall_score,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.db is not None:
            try:
                response = self.db.table("interviews").insert(record).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for interviews ({e}). Falling back to local store.")

        _in_memory_interviews[record_id] = record
        return record

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        memory_rec = _in_memory_interviews.get(record_id)
        if self.db is not None:
            try:
                response = self.db.table("interviews").select("*").eq("id", record_id).execute()
                if response.data:
                    db_rec = response.data[0]
                    if memory_rec:
                        merged = dict(db_rec)
                        merged.update({k: v for k, v in memory_rec.items() if k not in db_rec or v})
                        return merged
                    return db_rec
            except Exception as e:
                logger.warning(f"Supabase fetch failed for interviews ID {record_id}: {e}")

        return memory_rec

    async def list_by_profile_id(self, profile_id: str) -> List[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("interviews").select("*").eq("profile_id", profile_id).execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list failed for interviews profile {profile_id}: {e}")

        return [item for item in _in_memory_interviews.values() if item.get("profile_id") == profile_id]

    async def update(self, record_id: str, update_data: InterviewUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_by_id(record_id)

        if self.db is not None:
            try:
                response = self.db.table("interviews").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for interviews {record_id}: {e}")

        if record_id in _in_memory_interviews:
            _in_memory_interviews[record_id].update(fields_to_update)
            return _in_memory_interviews[record_id]

        return None

    async def delete(self, record_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("interviews").delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for interviews {record_id}: {e}")

        if record_id in _in_memory_interviews:
            del _in_memory_interviews[record_id]
            return True
        return False
