"""Typed state passed between recruitment graph nodes."""

from typing import TypedDict

from app.agents.schemas import (
    CandidateProfile,
    EvidenceAssessment,
    InterviewQuestion,
    JobRequirementAI,
    RecruiterRequirement,
    SecurityAnalysis,
    ScreeningReport,
)


class RecruitmentState(TypedDict, total=False):
    job_id: str
    candidate_id: str
    job_title: str
    job_description: str
    existing_requirements: list[RecruiterRequirement]
    normalized_requirements: list[JobRequirementAI]
    resume_text: str
    sanitized_resume_text: str
    security: SecurityAnalysis
    candidate_profile: CandidateProfile
    evidence_results: list[EvidenceAssessment]
    supported_requirements: list[JobRequirementAI]
    partial_requirements: list[JobRequirementAI]
    missing_requirements: list[JobRequirementAI]
    interview_questions: list[InterviewQuestion]
    final_report: ScreeningReport
    errors: list[str]
