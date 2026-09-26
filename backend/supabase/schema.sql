-- ============================================================================
-- PREPPILOT Supabase PostgreSQL Database Schema
-- Migration 001: Initial Core Platform Tables
-- ============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to automatically handle updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- 1. PROFILES TABLE
-- Stores user candidate profiles, education, target roles, skills & interests
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    name TEXT,
    email TEXT,
    education TEXT,
    degree TEXT,
    branch TEXT,
    graduation_year INT,
    target_role TEXT,
    experience_level TEXT,
    skills JSONB DEFAULT '[]'::jsonb,
    interests JSONB DEFAULT '[]'::jsonb,
    profile_data JSONB DEFAULT '{}'::jsonb,
    analysis JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schema migration additions for existing tables
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS profile_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS analysis JSONB DEFAULT '{}'::jsonb;


-- Index for user lookup
CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- Trigger for auto-updating updated_at
DROP TRIGGER IF EXISTS trigger_profiles_updated_at ON public.profiles;
CREATE TRIGGER trigger_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 2. SKILL_GAPS TABLE
-- Tracks targeted skill gaps between candidate current level & role requirements
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.skill_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    current_level TEXT NOT NULL,
    required_level TEXT NOT NULL,
    gap_score FLOAT NOT NULL CHECK (gap_score >= 0 AND gap_score <= 100),
    importance TEXT DEFAULT 'Medium', -- Low, Medium, High, Critical
    priority INT DEFAULT 1,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.skill_gaps ADD COLUMN IF NOT EXISTS priority INT DEFAULT 1;
ALTER TABLE public.skill_gaps ADD COLUMN IF NOT EXISTS reason TEXT;

CREATE INDEX IF NOT EXISTS idx_skill_gaps_profile_id ON public.skill_gaps(profile_id);



-- ============================================================================
-- 3. ROADMAPS TABLE
-- Stores AI-generated structured roadmap data for profile skill development
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    roadmap_data JSONB NOT NULL,
    duration_weeks INT DEFAULT 4 CHECK (duration_weeks > 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roadmaps_profile_id ON public.roadmaps(profile_id);

DROP TRIGGER IF EXISTS trigger_roadmaps_updated_at ON public.roadmaps;
CREATE TRIGGER trigger_roadmaps_updated_at
    BEFORE UPDATE ON public.roadmaps
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 4. ASSESSMENTS TABLE
-- Stores technical/behavioral skill assessments, questions, answers, and scores
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    assessment_type TEXT NOT NULL, -- e.g., technical, coding, aptitude, behavioral
    questions JSONB DEFAULT '[]'::jsonb,
    answers JSONB DEFAULT '[]'::jsonb,
    score FLOAT DEFAULT 0.0 CHECK (score >= 0 AND score <= 100),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_profile_id ON public.assessments(profile_id);


-- ============================================================================
-- 5. INTERVIEWS TABLE
-- Stores AI mock interview sessions, questions, answers, and AI feedback
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    questions JSONB DEFAULT '[]'::jsonb,
    answers JSONB DEFAULT '[]'::jsonb,
    feedback JSONB DEFAULT '{}'::jsonb,
    overall_score FLOAT DEFAULT 0.0 CHECK (overall_score >= 0 AND overall_score <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interviews_profile_id ON public.interviews(profile_id);


-- ============================================================================
-- 6. READINESS_SCORES TABLE
-- Tracks candidate career readiness scores across multiple dimensions
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.readiness_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    technical_score FLOAT DEFAULT 0.0 CHECK (technical_score >= 0 AND technical_score <= 100),
    skill_coverage_score FLOAT DEFAULT 0.0 CHECK (skill_coverage_score >= 0 AND skill_coverage_score <= 100),
    project_score FLOAT DEFAULT 0.0 CHECK (project_score >= 0 AND project_score <= 100),
    assessment_score FLOAT DEFAULT 0.0 CHECK (assessment_score >= 0 AND assessment_score <= 100),
    interview_score FLOAT DEFAULT 0.0 CHECK (interview_score >= 0 AND interview_score <= 100),
    overall_score FLOAT DEFAULT 0.0 CHECK (overall_score >= 0 AND overall_score <= 100),
    summary TEXT,
    improvement_priorities JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.readiness_scores ADD COLUMN IF NOT EXISTS skill_coverage_score FLOAT DEFAULT 0.0;
ALTER TABLE public.readiness_scores ADD COLUMN IF NOT EXISTS project_score FLOAT DEFAULT 0.0;
ALTER TABLE public.readiness_scores ADD COLUMN IF NOT EXISTS assessment_score FLOAT DEFAULT 0.0;
ALTER TABLE public.readiness_scores ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE public.readiness_scores ADD COLUMN IF NOT EXISTS improvement_priorities JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_readiness_scores_profile_id ON public.readiness_scores(profile_id);



-- ============================================================================
-- 7. PROGRESS TABLE
-- Tracks ongoing candidate skill learning status and completion percentages
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    status TEXT DEFAULT 'not_started', -- e.g. not_started, in_progress, completed
    progress_percentage FLOAT DEFAULT 0.0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_progress_profile_id ON public.progress(profile_id);

DROP TRIGGER IF EXISTS trigger_progress_updated_at ON public.progress;
CREATE TRIGGER trigger_progress_updated_at
    BEFORE UPDATE ON public.progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
