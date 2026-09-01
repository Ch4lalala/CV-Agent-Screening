"""Temporary non-persistent Phase 5 screening endpoint."""

from fastapi import APIRouter, HTTPException, status

from app.agents.schemas import ScreeningReport
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIStructuredOutputError
from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.services import screening_service

router = APIRouter(tags=["screening"])


@router.post(
    "/candidates/{candidate_id}/screen",
    response_model=ScreeningReport,
)
async def screen_candidate(
    candidate_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> ScreeningReport:
    try:
        return await screening_service.screen_candidate(
            db,
            candidate_id=candidate_id,
            user_id=user.id,
        )
    except screening_service.ScreeningInputNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except screening_service.ResumeNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        ) from exc
    except (AIProviderError, AIStructuredOutputError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI screening is temporarily unavailable",
        ) from exc
    except screening_service.ScreeningExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete candidate screening",
        ) from exc
