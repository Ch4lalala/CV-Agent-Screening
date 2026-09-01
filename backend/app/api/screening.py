"""Persisted candidate screening and report endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.schemas.screening import CandidateReportResponse, ScreeningRunResponse
from app.services import screening_service

router = APIRouter(tags=["screening"])


@router.post(
    "/candidates/{candidate_id}/screen",
    response_model=CandidateReportResponse,
)
async def screen_candidate(
    candidate_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> CandidateReportResponse:
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
    except screening_service.ScreeningAlreadyProcessingError as exc:
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


def _report_read_error(exc: Exception) -> HTTPException:
    if isinstance(exc, screening_service.ScreeningInputNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, screening_service.ScreeningReportNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to load candidate screening report",
    )


@router.get(
    "/candidates/{candidate_id}/screening",
    response_model=CandidateReportResponse,
)
def get_latest_screening(
    candidate_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> CandidateReportResponse:
    try:
        return screening_service.get_latest_report(
            db,
            candidate_id=candidate_id,
            user_id=user.id,
        )
    except (
        screening_service.ScreeningInputNotFoundError,
        screening_service.ScreeningReportNotFoundError,
        screening_service.ScreeningExecutionError,
    ) as exc:
        raise _report_read_error(exc) from exc


@router.get(
    "/candidates/{candidate_id}/screenings",
    response_model=list[ScreeningRunResponse],
)
def list_screenings(
    candidate_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> list[ScreeningRunResponse]:
    try:
        return screening_service.list_screening_runs(
            db,
            candidate_id=candidate_id,
            user_id=user.id,
        )
    except screening_service.ScreeningInputNotFoundError as exc:
        raise _report_read_error(exc) from exc


@router.get(
    "/candidates/{candidate_id}/screenings/{screening_run_id}",
    response_model=CandidateReportResponse,
)
def get_screening(
    candidate_id: int,
    screening_run_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> CandidateReportResponse:
    try:
        return screening_service.get_screening_report(
            db,
            candidate_id=candidate_id,
            screening_run_id=screening_run_id,
            user_id=user.id,
        )
    except (
        screening_service.ScreeningInputNotFoundError,
        screening_service.ScreeningReportNotFoundError,
        screening_service.ScreeningExecutionError,
    ) as exc:
        raise _report_read_error(exc) from exc
