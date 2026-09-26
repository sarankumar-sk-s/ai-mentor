# PrepPilot Backend API

PrepPilot Backend built with **FastAPI**, **Pydantic**, **Supabase (PostgreSQL)**, and **Google Gemini AI**.

---

## 🏗 Project Architecture & Database Schema

```text
React / Vite Frontend
        │ REST API
FastAPI Backend
        ├── Supabase PostgreSQL Database (7 Core Tables)
        └── Google Gemini AI Service Abstraction Layer
```

---

## 📐 Phase 4: Transparent Readiness Scoring Model

PrepPilot uses a transparent, hybrid scoring model combining **deterministic math calculations** for sub-scores with **Google Gemini AI** for qualitative career mentorship & improvement priorities.

### Sub-Score Formulas & Weights

| Component | Weight | Calculation Formula |
| :--- | :--- | :--- |
| **`technical_score`** | **25%** | $\min(100.0, (\text{skills\_count} \times 15.0) + (\text{certs\_count} \times 12.5))$ |
| **`skill_coverage_score`** | **25%** | $\min(100.0, \frac{\text{unique\_skills\_count}}{6.0} \times 100.0)$ |
| **`project_score`** | **20%** | $\min(100.0, (\text{projects\_count} \times 35.0) + 10.0)$ |
| **`assessment_score`** | **15%** | Average score across recorded technical assessments (Defaults to $70.0$) |
| **`interview_score`** | **15%** | Average overall score across recorded AI mock interviews (Defaults to $70.0$) |

### Overall Readiness Formula
$$\text{Overall Score} = 0.25 \cdot \text{technical} + 0.25 \cdot \text{skill\_coverage} + 0.20 \cdot \text{project} + 0.15 \cdot \text{assessment} + 0.15 \cdot \text{interview}$$

---

## 🚀 POST /api/readiness/calculate

Calculates candidate readiness sub-scores and generates qualitative mentorship feedback using Gemini AI.

### Example Request Body

```json
{
  "profile_id": "usr_987654321",
  "target_role": "Backend Software Engineer",
  "experience_level": "beginner",
  "skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
  "projects": ["PrepPilot AI Backend", "Attendance Tracker"],
  "certifications": ["AWS Certified Developer Associate"]
}
```

### Example Response Body (HTTP 200 OK)

```json
{
  "profile_id": "f47ac10b-58cc-5372-a567-0e02b2c3d479",
  "overall_score": 78.67,
  "technical_score": 72.5,
  "skill_coverage_score": 66.67,
  "project_score": 80.0,
  "assessment_score": 70.0,
  "interview_score": 70.0,
  "summary": "The candidate exhibits strong core backend development readiness for Backend Software Engineer, supported by solid project implementation.",
  "improvement_priorities": [
    "Expand skill coverage into containerization (Docker).",
    "Build a production-grade microservice architecture.",
    "Complete mock technical interviews to boost interview performance score."
  ],
  "created_at": "2026-09-26T11:34:00+00:00"
}
```

---

## 🎯 Phase 5: Skill Gap Analysis Engine

PrepPilot compares a student's **Current Skills** against the **Required Skills for Target Role** using Gemini AI for contextual relevance & explanations, paired with deterministic Python backend validation:

1. **Numerical Clamping**: `gap_score` is clamped strictly to `[0.0, 100.0]`.
2. **Importance Normalization**: Normalized to `Critical`, `High`, `Medium`, or `Low`.
3. **Deterministic Ranking & Priority**: Sorted by Importance rank (`Critical`=1, `High`=2, `Medium`=3, `Low`=4) and `gap_score` descending, then assigned priority integers `1, 2, 3...`.

---

## 🚀 POST /api/skills/analyze/{profile_id}

Triggers Skill Gap Analysis comparing current student skills against target role requirements.

### Example Request Body

```json
{
  "target_role": "Backend Software Engineer",
  "skills": ["Python", "SQL", "Git", "HTML", "CSS"]
}
```

### Example Response Body (HTTP 200 OK)

```json
{
  "profile_id": "f47ac10b-58cc-5372-a567-0e02b2c3d479",
  "target_role": "Backend Software Engineer",
  "total_gaps_identified": 2,
  "skill_gaps": [
    {
      "skill": "Docker & Containerization",
      "current_level": "None",
      "required_level": "Intermediate",
      "gap_score": 80.0,
      "importance": "Critical",
      "priority": 1,
      "reason": "Essential for containerizing microservices in modern cloud deployments."
    },
    {
      "skill": "PostgreSQL & Query Optimization",
      "current_level": "Beginner",
      "required_level": "Advanced",
      "gap_score": 65.0,
      "importance": "High",
      "priority": 2,
      "reason": "Core database engine for production backend services."
    }
  ]
}
```

---

## 📡 API Endpoints Matrix

| Module | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/api/health` | Health status for backend, Supabase DB & Gemini AI |
| **Profile Analysis** | `POST` | `/api/profile/analyze` | Gemini AI structured output candidate profile analysis |
| **Profiles** | `POST` | `/api/profile` | Create candidate profile |
| | `GET` | `/api/profile` | List all profiles |
| | `GET` | `/api/profile/{id}` | Get profile details by ID |
| | `PUT` | `/api/profile/{id}` | Update profile details |
| | `DELETE` | `/api/profile/{id}` | Delete profile |
| **Readiness Scores** | `POST` | `/api/readiness/calculate` | Calculate readiness score with Gemini feedback |
| | `GET` | `/api/readiness/{profile_id}` | Get candidate readiness score by profile ID |
| | `GET` | `/api/readiness/profile/{profile_id}` | List readiness evaluation history |
| | `POST` | `/api/readiness` | Create readiness score entry |
| | `PUT` | `/api/readiness/{id}` | Update readiness score entry |
| | `DELETE` | `/api/readiness/{id}` | Delete readiness score entry |
| **Skill Gaps** | `POST` | `/api/skills/analyze/{profile_id}` | Analyze candidate skill gaps vs target role |
| | `GET` | `/api/skills/gaps/{profile_id}` | Get identified skill gaps by profile ID |
| | `POST` | `/api/skill-gaps` | Create manual skill gap entry |
| | `GET` | `/api/skill-gaps/profile/{profile_id}` | List skill gaps for candidate profile |
| | `GET` | `/api/skill-gaps/{id}` | Get skill gap by ID |
| | `PUT` | `/api/skill-gaps/{id}` | Update skill gap by ID |
| | `DELETE` | `/api/skill-gaps/{id}` | Delete skill gap by ID |
| **Roadmaps** | `POST` | `/api/roadmaps` | Create learning roadmap |
| | `GET` | `/api/roadmaps/profile/{profile_id}` | List roadmaps for candidate profile |
| **Assessments** | `POST` | `/api/assessments` | Create assessment record |
| | `GET` | `/api/assessments/profile/{profile_id}` | List assessments for profile |
| **Mock Interviews** | `POST` | `/api/interviews` | Create mock interview session |
| | `GET` | `/api/interviews/profile/{profile_id}` | List mock interviews for profile |
| **Progress Tracking** | `POST` | `/api/progress` | Create progress tracking entry |
| | `GET` | `/api/progress/profile/{profile_id}` | List progress tracking for profile |

