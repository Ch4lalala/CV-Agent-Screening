"""Targeted interview question generation node."""

from app.agents.prompts import interview_messages
from app.agents.schemas import InterviewQuestionsResponse
from app.agents.state import RecruitmentState
from app.ai.client import AIClient
from app.services.interview_service import (
    eligible_uncertainties,
    reconcile_interview_questions,
)


async def generate_interview_questions(
    state: RecruitmentState,
    *,
    ai_client: AIClient,
) -> dict[str, object]:
    eligible = eligible_uncertainties(state["evidence_results"])
    if not eligible:
        return {"interview_questions": []}

    response = await ai_client.invoke_structured(
        InterviewQuestionsResponse,
        interview_messages(eligible),
    )
    return {
        "interview_questions": reconcile_interview_questions(
            state["evidence_results"], response
        )
    }
