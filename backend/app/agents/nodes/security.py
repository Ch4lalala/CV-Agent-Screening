"""Resume security node with a conservative failure fallback."""

import logging

from app.agents.schemas import SecurityAnalysis
from app.agents.state import RecruitmentState
from app.ai.client import AIClient
from app.services.security_service import analyze_resume_security

logger = logging.getLogger(__name__)


async def check_resume_security(
    state: RecruitmentState,
    *,
    ai_client: AIClient,
) -> dict[str, object]:
    try:
        result = await analyze_resume_security(
            state["resume_text"],
            ai_client=ai_client,
        )
        return {
            "security": result.security,
            "sanitized_resume_text": result.sanitized_resume_text,
        }
    except Exception as exc:
        logger.warning(
            "security_scan_unavailable failure_type=%s",
            type(exc).__name__,
            extra={"failure_type": type(exc).__name__},
        )
        # Empty evaluation context is safer than passing unscanned document text.
        return {
            "security": SecurityAnalysis(status="unavailable", flags=[]),
            "sanitized_resume_text": "",
        }
