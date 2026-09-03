"""Deterministic, decision-free screening report assembly."""

from app.agents.schemas import CoverageSummary, SecurityAnalysis, ScreeningReport
from app.agents.state import RecruitmentState


def build_screening_report(state: RecruitmentState) -> ScreeningReport:
    requirements = state["normalized_requirements"]
    assessments = state["evidence_results"]

    required = [item for item in requirements if item.requirement_type == "required"]
    preferred = [
        item for item in requirements if item.requirement_type == "preferred"
    ]
    required_supported = sum(
        item.status == "supported"
        for item in assessments
        if item.requirement_type == "required"
    )
    preferred_supported = sum(
        item.status == "supported"
        for item in assessments
        if item.requirement_type == "preferred"
    )

    return ScreeningReport(
        job_id=state["job_id"],
        candidate_id=state["candidate_id"],
        job_title=state["job_title"],
        normalized_requirements=requirements,
        candidate_profile=state["candidate_profile"],
        required_coverage=CoverageSummary(
            supported=required_supported,
            total=len(required),
        ),
        preferred_coverage=CoverageSummary(
            supported=preferred_supported,
            total=len(preferred),
        ),
        evidence_results=assessments,
        needs_verification=[
            item.requirement
            for item in assessments
            if item.needs_human_verification
        ],
        interview_questions=state["interview_questions"],
        security=state.get(
            "security",
            SecurityAnalysis(status="unavailable", flags=[]),
        ),
        security_warning=None,
    )
