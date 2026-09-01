"""Job requirement normalization node."""

from app.agents.prompts import requirements_messages
from app.agents.schemas import JobRequirementsResponse
from app.agents.state import RecruitmentState
from app.ai.client import AIClient
from app.services.requirement_normalization_service import reconcile_requirements


async def normalize_requirements(
    state: RecruitmentState,
    *,
    ai_client: AIClient,
) -> dict[str, object]:
    response = await ai_client.invoke_structured(
        JobRequirementsResponse,
        requirements_messages(
            job_title=state["job_title"],
            job_description=state["job_description"],
            existing_requirements=state.get("existing_requirements", []),
        ),
    )
    return {
        "normalized_requirements": reconcile_requirements(
            state.get("existing_requirements", []), response
        )
    }
