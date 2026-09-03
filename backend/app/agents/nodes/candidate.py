"""Candidate profile extraction node."""

from app.agents.prompts import candidate_profile_messages
from app.agents.schemas import CandidateProfile
from app.agents.state import RecruitmentState
from app.ai.client import AIClient
from app.services.candidate_profile_service import retain_candidate_provided_urls


async def extract_candidate_profile(
    state: RecruitmentState,
    *,
    ai_client: AIClient,
) -> dict[str, object]:
    profile = await ai_client.invoke_structured(
        CandidateProfile,
        candidate_profile_messages(state["sanitized_resume_text"]),
    )
    return {
        "candidate_profile": retain_candidate_provided_urls(
            profile,
            state["sanitized_resume_text"],
        )
    }
