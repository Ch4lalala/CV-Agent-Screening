"""Deterministic uncertainty grouping node."""

from app.agents.state import RecruitmentState
from app.services.evidence_service import group_requirements_by_evidence


def analyze_uncertainty(state: RecruitmentState) -> dict[str, object]:
    return group_requirements_by_evidence(
        state["normalized_requirements"],
        state["evidence_results"],
    )
