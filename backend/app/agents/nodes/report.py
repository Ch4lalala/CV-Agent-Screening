"""Deterministic screening report node."""

from app.agents.state import RecruitmentState
from app.services.report_service import build_screening_report


def generate_report(state: RecruitmentState) -> dict[str, object]:
    return {"final_report": build_screening_report(state)}
