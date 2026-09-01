"""Batched evidence matching and deterministic quote validation node."""

from app.agents.prompts import evidence_messages
from app.agents.schemas import EvidenceAnalysisResponse
from app.agents.state import RecruitmentState
from app.ai.client import AIClient
from app.services.evidence_service import validate_evidence_assessments


async def match_evidence(
    state: RecruitmentState,
    *,
    ai_client: AIClient,
) -> dict[str, object]:
    requirements = state["normalized_requirements"]
    if not requirements:
        return {"evidence_results": []}

    response = await ai_client.invoke_structured(
        EvidenceAnalysisResponse,
        evidence_messages(
            requirements=requirements,
            candidate_profile=state["candidate_profile"],
            resume_text=state["resume_text"],
        ),
    )
    return {
        "evidence_results": validate_evidence_assessments(
            requirements,
            response,
            state["resume_text"],
        )
    }
