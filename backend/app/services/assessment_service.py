import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.database import get_supabase_client
from app.schemas.assessment import (
    AssessmentGenerateRequestSchema,
    AssessmentSubmitRequestSchema,
    AssessmentCreateSchema,
    AssessmentUpdateSchema
)
from app.services.gemini_service import GeminiService
from app.services.profile_service import ProfileService
from app.services.skill_gap_service import SkillGapService

logger = logging.getLogger(__name__)

_in_memory_assessments: Dict[str, Dict[str, Any]] = {}

ASSESSMENT_GENERATION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "question": {"type": "string"},
                    "type": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "correct_answer": {"type": "string"},
                    "difficulty": {"type": "string"},
                    "skill": {"type": "string"}
                },
                "required": ["question_id", "question", "type", "correct_answer", "difficulty", "skill"]
            }
        }
    },
    "required": ["questions"]
}

QUALITATIVE_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "is_correct": {"type": "boolean"},
        "feedback": {"type": "string"}
    },
    "required": ["score", "is_correct", "feedback"]
}

def _sanitize_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strips correct_answer field from questions array before submission."""
    sanitized = []
    for q in questions:
        q_copy = dict(q)
        q_copy.pop("correct_answer", None)
        sanitized.append(q_copy)
    return sanitized

def _generate_fallback_questions(
    target_role: str,
    selected_topic: str,
    skill_gaps: List[str],
    difficulty: str,
    num_questions: int
) -> List[Dict[str, Any]]:
    gaps = skill_gaps or ["Core Fundamentals", "Problem Solving", "System Design"]
    questions = []

    for i in range(1, num_questions + 1):
        skill = gaps[(i - 1) % len(gaps)]
        q_id = f"q_{i}"

        if i % 3 == 1:
            # MCQ
            questions.append({
                "question_id": q_id,
                "question": f"Which of the following best describes the core purpose of {skill} in {target_role} applications?",
                "type": "mcq",
                "options": [
                    f"Optimizing efficiency and reliability of {skill}",
                    f"Replacing basic programming syntax",
                    f"Managing static client design assets",
                    f"Bypassing runtime validation checks"
                ],
                "correct_answer": f"Optimizing efficiency and reliability of {skill}",
                "difficulty": difficulty,
                "skill": skill
            })
        elif i % 3 == 2:
            # Conceptual
            questions.append({
                "question_id": q_id,
                "question": f"Explain key architectural trade-offs and best practices when implementing {skill} for {selected_topic}.",
                "type": "conceptual",
                "options": [],
                "correct_answer": f"Implementation of {skill} requires balance between execution complexity, memory footprint, maintainability, and error handling.",
                "difficulty": difficulty,
                "skill": skill
            })
        else:
            # Coding
            questions.append({
                "question_id": q_id,
                "question": f"Write a code snippet demonstrating error-handled initialization and execution of {skill}.",
                "type": "coding",
                "options": [],
                "correct_answer": f"Defines modular function for {skill}, validates input data, handles exceptions cleanly, and returns validated output.",
                "difficulty": difficulty,
                "skill": skill
            })

    return questions

class AssessmentService:
    """
    Repository & Service layer managing AI assessment generation, submission evaluation,
    deterministic & qualitative scoring, and Supabase persistence.
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

    async def generate_assessment(
        self,
        request_data: AssessmentGenerateRequestSchema
    ) -> Dict[str, Any]:
        """
        Generates a structured AI assessment tailored to student's skill gaps, target role,
        difficulty, and selected topic. Questions include MCQ, coding, and conceptual formats.
        """
        profile_id = request_data.profile_id
        target_role = request_data.target_role or "Software Engineer"
        selected_topic = request_data.selected_topic or "Technical Assessment"
        difficulty = request_data.difficulty or "intermediate"
        num_questions = request_data.num_questions or 5
        skill_gaps = list(request_data.skill_gaps or [])

        # Fetch profile context if profile_id provided
        if profile_id:
            profile_record = await self.profile_service.get_profile_by_id(profile_id)
            if profile_record:
                target_role = request_data.target_role or profile_record.get("target_role") or target_role
                if not skill_gaps:
                    gap_records = await self.skill_gap_service.list_by_profile_id(profile_id)
                    skill_gaps = [g.get("skill") for g in gap_records if g.get("skill")] or profile_record.get("analysis", {}).get("skill_gaps") or []

        questions = None

        if self.gemini_service and self.gemini_service.is_configured():
            prompt = f"""
            You are an expert technical interviewer and AI assessment builder.
            Generate a high-quality technical assessment with exactly {num_questions} questions for a candidate targeting '{target_role}'.

            Assessment Context:
            - Selected Topic / Domain: {selected_topic}
            - Difficulty Level: {difficulty}
            - Targeted Candidate Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'Core role skills'}

            REQUIREMENTS:
            1. Include a balanced mix of question types: 'mcq', 'coding', and 'conceptual'.
            2. For 'mcq' questions, provide exactly 4 distinct choices in 'options' and the exact correct string in 'correct_answer'.
            3. For 'coding' and 'conceptual' questions, set 'options' to an empty list [], and set 'correct_answer' to a detailed reference solution / evaluation criteria.
            4. Each question MUST have:
               - question_id: unique string (e.g. 'q1', 'q2', ...)
               - question: detailed question text
               - type: 'mcq' | 'coding' | 'conceptual'
               - options: list of string options for MCQ, empty [] otherwise
               - correct_answer: string correct answer / model solution
               - difficulty: '{difficulty}'
               - skill: target skill name

            Output strictly valid JSON conforming to the schema.
            """

        source_tag = "fallback"
        if self.gemini_service and self.gemini_service.is_configured():
            try:
                ai_res = await self.gemini_service.generate_structured(
                    prompt=prompt,
                    schema=ASSESSMENT_GENERATION_SCHEMA,
                    model="gemini-3.1-flash-lite"
                )
                if isinstance(ai_res, dict) and "questions" in ai_res and len(ai_res["questions"]) > 0:
                    questions = ai_res["questions"]
                    source_tag = ai_res.get("_source", "gemini")
            except Exception as exc:
                logger.warning(f"Gemini assessment question generation failed: {exc}. Using fallback questions.")

        if not questions:
            source_tag = "fallback"
            questions = _generate_fallback_questions(
                target_role=target_role,
                selected_topic=selected_topic,
                skill_gaps=skill_gaps,
                difficulty=difficulty,
                num_questions=num_questions
            )

        now = datetime.now(timezone.utc).isoformat()
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": profile_id,
            "target_role": target_role,
            "selected_topic": selected_topic,
            "difficulty": difficulty,
            "status": "pending",
            "source": source_tag,
            "assessment_type": "technical",
            "questions": questions,
            "answers": [],
            "score": 0.0,
            "evaluation_result": None,
            "created_at": now,
            "submitted_at": None
        }

        if self.db is not None:
            try:
                response = self.db.table("assessments").insert(record).execute()
                if response.data:
                    logger.info(f"Created assessment record {record_id} in Supabase")
                    record = response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for assessments ({e}). Storing in local fallback.")

        _in_memory_assessments[record_id] = record

        # Return sanitized response hiding correct_answer
        sanitized_record = dict(record)
        sanitized_record["questions"] = _sanitize_questions(record["questions"])
        return sanitized_record

    async def get_assessment_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves assessment by ID. Sanitizes questions if unsubmitted to prevent exposing correct answers.
        """
        record = await self.get_by_id(record_id)
        if not record:
            return None

        # Copy to avoid mutating internal state
        result_record = dict(record)
        if result_record.get("status") != "submitted":
            result_record["questions"] = _sanitize_questions(result_record.get("questions", []))

        return result_record

    async def submit_assessment(
        self,
        record_id: str,
        submit_data: AssessmentSubmitRequestSchema
    ) -> Dict[str, Any]:
        """
        Submits candidate answers for evaluation:
        1. Validates submitted answers.
        2. Calculates objective scores deterministically for MCQ questions.
        3. Uses Gemini for qualitative evaluation of coding & conceptual questions.
        4. Identifies candidate weak areas and overall feedback.
        5. Stores result in Supabase and updates readiness score inputs.
        """
        record = await self.get_by_id(record_id)
        if not record:
            raise ValueError(f"Assessment with ID '{record_id}' not found.")

        questions = record.get("questions", [])
        answers_map = {a.question_id: a.user_answer for a in submit_data.answers}

        evaluations = []
        scores = []
        weak_skills = []
        correct_count = 0

        for q in questions:
            q_id = q.get("question_id")
            q_type = str(q.get("type", "mcq")).lower()
            q_text = q.get("question", "")
            correct_ans = str(q.get("correct_answer", "")).strip()
            user_ans = str(answers_map.get(q_id, "")).strip()
            skill = q.get("skill", "General Skill")

            q_score = 0.0
            is_correct = False
            feedback = ""

            if q_type == "mcq":
                # Deterministic scoring for MCQ
                if user_ans and (user_ans.lower() == correct_ans.lower() or user_ans.lower() in correct_ans.lower() or correct_ans.lower() in user_ans.lower()):
                    q_score = 100.0
                    is_correct = True
                    feedback = "Correct option selected."
                    correct_count += 1
                else:
                    q_score = 0.0
                    is_correct = False
                    feedback = f"Incorrect. Correct answer is: '{correct_ans}'."
                    weak_skills.append(skill)
            else:
                # Qualitative evaluation for coding & conceptual
                if not user_ans:
                    q_score = 0.0
                    is_correct = False
                    feedback = "No answer provided."
                    weak_skills.append(skill)
                else:
                    evaluated = False
                    if self.gemini_service and self.gemini_service.is_configured():
                        prompt = f"""
                        Evaluate this candidate's technical response for a {q_type} assessment question.

                        Question ({skill}): {q_text}
                        Expected Reference Solution / Criteria: {correct_ans}
                        Candidate's Submitted Answer: {user_ans}

                        Assess accuracy, completeness, and correctness. Return JSON with:
                        - score: float between 0.0 and 100.0
                        - is_correct: boolean (true if score >= 70.0)
                        - feedback: constructive feedback sentence
                        """
                        try:
                            eval_res = await self.gemini_service.generate_structured(
                                prompt=prompt,
                                schema=QUALITATIVE_EVALUATION_SCHEMA,
                                model="gemini-3.1-flash-lite"
                            )
                            if isinstance(eval_res, dict):
                                q_score = float(eval_res.get("score", 50.0))
                                is_correct = bool(eval_res.get("is_correct", q_score >= 70.0))
                                feedback = str(eval_res.get("feedback", "Qualitative evaluation complete."))
                                evaluated = True
                                if is_correct:
                                    correct_count += 1
                                else:
                                    weak_skills.append(skill)
                        except Exception as exc:
                            logger.warning(f"Qualitative Gemini evaluation failed for question {q_id}: {exc}")

                    if not evaluated:
                        # Fallback heuristic evaluation for coding/conceptual
                        if len(user_ans) > 15:
                            q_score = 80.0
                            is_correct = True
                            feedback = f"Good {q_type} submission covering key concepts of {skill}."
                            correct_count += 1
                        else:
                            q_score = 40.0
                            is_correct = False
                            feedback = f"Incomplete submission for {skill}. Review core concepts."
                            weak_skills.append(skill)

            scores.append(q_score)
            evaluations.append({
                "question_id": q_id,
                "question": q_text,
                "type": q_type,
                "skill": skill,
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "score": q_score,
                "feedback": feedback
            })

        total_q = len(questions) or 1
        overall_score = round(sum(scores) / total_q, 2)
        unique_weak_areas = list(dict.fromkeys(weak_skills))

        overall_feedback = (
            f"Candidate completed the assessment with an overall score of {overall_score}/100 "
            f"({correct_count}/{total_q} questions answered correctly)."
        )
        if unique_weak_areas:
            overall_feedback += f" Focus on strengthening identified weak areas: {', '.join(unique_weak_areas)}."

        now = datetime.now(timezone.utc).isoformat()
        submitted_answers = [a.model_dump() for a in submit_data.answers]

        eval_result = {
            "assessment_id": record_id,
            "profile_id": record.get("profile_id"),
            "target_role": record.get("target_role", "Software Engineer"),
            "selected_topic": record.get("selected_topic", "Technical Assessment"),
            "difficulty": record.get("difficulty", "intermediate"),
            "overall_score": overall_score,
            "total_questions": total_q,
            "correct_count": correct_count,
            "weak_areas": unique_weak_areas,
            "overall_feedback": overall_feedback,
            "submitted_at": now,
            "question_evaluations": evaluations
        }

        fields_to_update = {
            "status": "submitted",
            "answers": submitted_answers,
            "score": overall_score,
            "feedback": overall_feedback,
            "evaluation_result": eval_result,
            "submitted_at": now
        }

        if self.db is not None:
            try:
                response = self.db.table("assessments").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    record = response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for assessment submit {record_id}: {e}")

        if record_id in _in_memory_assessments:
            _in_memory_assessments[record_id].update(fields_to_update)
            record = _in_memory_assessments[record_id]

        return eval_result

    async def get_assessment_result(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the completed evaluation result for an assessment.
        """
        record = await self.get_by_id(record_id)
        if not record:
            return None

        if record.get("status") != "submitted" or not record.get("evaluation_result"):
            return None

        return record.get("evaluation_result")

    async def create_assessment(self, data: AssessmentCreateSchema) -> Dict[str, Any]:
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "profile_id": data.profile_id,
            "assessment_type": data.assessment_type,
            "questions": data.questions,
            "answers": data.answers,
            "score": data.score,
            "feedback": data.feedback,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.db is not None:
            try:
                response = self.db.table("assessments").insert(record).execute()
                if response.data:
                    logger.info(f"Created assessment record {record_id} in Supabase")
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase insert failed for assessments ({e}). Falling back to local store.")

        _in_memory_assessments[record_id] = record
        return record

    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("assessments").select("*").eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase fetch failed for assessments ID {record_id}: {e}")

        return _in_memory_assessments.get(record_id)

    async def list_by_profile_id(self, profile_id: str) -> List[Dict[str, Any]]:
        if self.db is not None:
            try:
                response = self.db.table("assessments").select("*").eq("profile_id", profile_id).execute()
                if response.data:
                    return response.data
            except Exception as e:
                logger.warning(f"Supabase list failed for assessments profile {profile_id}: {e}")

        return [item for item in _in_memory_assessments.values() if item.get("profile_id") == profile_id]

    async def update(self, record_id: str, update_data: AssessmentUpdateSchema) -> Optional[Dict[str, Any]]:
        fields_to_update = {k: v for k, v in update_data.model_dump().items() if v is not None}
        if not fields_to_update:
            return await self.get_by_id(record_id)

        if self.db is not None:
            try:
                response = self.db.table("assessments").update(fields_to_update).eq("id", record_id).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.warning(f"Supabase update failed for assessments {record_id}: {e}")

        if record_id in _in_memory_assessments:
            _in_memory_assessments[record_id].update(fields_to_update)
            return _in_memory_assessments[record_id]

        return None

    async def delete(self, record_id: str) -> bool:
        if self.db is not None:
            try:
                self.db.table("assessments").delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.warning(f"Supabase delete failed for assessments {record_id}: {e}")

        if record_id in _in_memory_assessments:
            del _in_memory_assessments[record_id]
            return True
        return False
