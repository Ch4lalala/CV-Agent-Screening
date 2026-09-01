"""Coordinate screening inputs, run lifecycle, graph execution, and report reads."""

import logging
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.graph import get_recruitment_graph
from app.agents.schemas import RecruiterRequirement, ScreeningReport
from app.agents.state import RecruitmentState
from app.ai.config import get_configured_ai_model_name
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.models.candidate import Candidate
from app.models.enums import CandidateStatus, ResumeExtractionStatus, ScreeningRunStatus
from app.models.screening_run import ScreeningRun
from app.repositories import (
    candidates,
    job_requirements,
    jobs,
    resume_documents,
    screening_runs,
)
from app.schemas.screening import CandidateReportResponse, ScreeningRunResponse
from app.services import screening_persistence_service

logger = logging.getLogger(__name__)


class ScreeningInputNotFoundError(Exception):
    pass


class ResumeNotReadyError(Exception):
    pass


class ScreeningAlreadyProcessingError(Exception):
    pass


class ScreeningReportNotFoundError(Exception):
    pass


class ScreeningExecutionError(Exception):
    pass


def _safe_failure_message(exc: Exception) -> str:
    if isinstance(exc, AIConfigurationError):
        return "AI service is not configured."
    if isinstance(exc, AIProviderError):
        return "AI provider is temporarily unavailable."
    if isinstance(exc, AIStructuredOutputError):
        return "AI returned an invalid structured response."
    return "Candidate screening failed."


def _start_screening(
    db: Session, *, candidate_id: int, user_id: int
) -> tuple[ScreeningRun, RecruitmentState, set[int]]:
    candidate = screening_runs.candidate_for_user_for_update(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    if candidate is None:
        db.rollback()
        raise ScreeningInputNotFoundError("Candidate not found")

    job = jobs.get_for_user(db, job_id=candidate.job_id, user_id=user_id)
    if job is None:
        db.rollback()
        raise ScreeningInputNotFoundError("Job not found")

    resume = resume_documents.get_for_candidate(db, candidate_id=candidate.id)
    if resume is None:
        db.rollback()
        raise ScreeningInputNotFoundError("Resume not found")
    if (
        resume.extraction_status != ResumeExtractionStatus.COMPLETED
        or not resume.extracted_text
    ):
        db.rollback()
        raise ResumeNotReadyError("Resume extraction is not completed")

    if (
        candidate.status == CandidateStatus.PROCESSING
        or screening_runs.has_processing_run(db, candidate_id=candidate.id)
    ):
        db.rollback()
        raise ScreeningAlreadyProcessingError(
            "Candidate screening is already in progress."
        )

    requirements = job_requirements.list_for_job(db, job_id=job.id)
    valid_requirement_ids = {item.id for item in requirements}
    initial_state: RecruitmentState = {
        "job_id": str(job.id),
        "candidate_id": str(candidate.id),
        "job_title": job.title,
        "job_description": job.description,
        "existing_requirements": [
            RecruiterRequirement(
                id=item.id,
                name=item.name,
                description=item.description,
                requirement_type=item.requirement_type.value,
                priority=item.priority,
            )
            for item in requirements
        ],
        "resume_text": resume.extracted_text,
        "errors": [],
    }

    run = ScreeningRun(
        candidate_id=candidate.id,
        status=ScreeningRunStatus.PROCESSING,
        model_name=get_configured_ai_model_name(),
        started_at=datetime.now(UTC),
    )
    candidate.status = CandidateStatus.PROCESSING
    db.add(run)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if screening_runs.has_processing_run(db, candidate_id=candidate_id):
            raise ScreeningAlreadyProcessingError(
                "Candidate screening is already in progress."
            ) from exc
        raise ScreeningExecutionError("Unable to start candidate screening") from exc

    return run, initial_state, valid_requirement_ids


async def screen_candidate(
    db: Session,
    *,
    candidate_id: int,
    user_id: int,
    graph: object | None = None,
) -> CandidateReportResponse:
    """Create a run, execute the graph outside a transaction, and persist it."""

    run, initial_state, valid_requirement_ids = _start_screening(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    logger.info(
        "screening_started",
        extra={
            "candidate_id": candidate_id,
            "job_id": initial_state["job_id"],
            "screening_run_id": run.id,
        },
    )

    try:
        screening_graph = graph or get_recruitment_graph()
        result = await screening_graph.ainvoke(initial_state)  # type: ignore[union-attr]
        report = ScreeningReport.model_validate(result["final_report"])
        completed_run = screening_persistence_service.persist_completed_report(
            db,
            run=run,
            report=report,
            valid_requirement_ids=valid_requirement_ids,
        )
    except (AIConfigurationError, AIProviderError, AIStructuredOutputError) as exc:
        _record_failed_run(db, run_id=run.id, candidate_id=candidate_id, exc=exc)
        raise
    except (KeyError, TypeError, ValidationError) as exc:
        _record_failed_run(db, run_id=run.id, candidate_id=candidate_id, exc=exc)
        raise ScreeningExecutionError("Candidate screening failed") from exc
    except screening_persistence_service.ScreeningPersistenceError as exc:
        _record_failed_run(db, run_id=run.id, candidate_id=candidate_id, exc=exc)
        raise ScreeningExecutionError("Candidate screening failed") from exc
    except Exception as exc:
        _record_failed_run(db, run_id=run.id, candidate_id=candidate_id, exc=exc)
        raise ScreeningExecutionError("Candidate screening failed") from exc

    logger.info(
        "screening_completed",
        extra={"candidate_id": candidate_id, "screening_run_id": run.id},
    )
    return _build_report_or_error(completed_run)


def _record_failed_run(
    db: Session,
    *,
    run_id: int,
    candidate_id: int,
    exc: Exception,
) -> None:
    logger.warning(
        "screening_failed",
        extra={
            "candidate_id": candidate_id,
            "screening_run_id": run_id,
            "failure_type": type(exc).__name__,
        },
    )
    try:
        screening_persistence_service.mark_failed(
            db,
            run_id=run_id,
            candidate_id=candidate_id,
            error_message=_safe_failure_message(exc),
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Unable to persist failed screening state",
            extra={"candidate_id": candidate_id, "screening_run_id": run_id},
        )


def _build_report_or_error(run: ScreeningRun) -> CandidateReportResponse:
    try:
        return screening_persistence_service.build_candidate_report(run)
    except screening_persistence_service.ScreeningPersistenceError as exc:
        raise ScreeningExecutionError("Unable to load screening report") from exc


def _candidate_for_user_or_error(
    db: Session, *, candidate_id: int, user_id: int
) -> Candidate:
    candidate = candidates.get_for_user(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    if candidate is None:
        raise ScreeningInputNotFoundError("Candidate not found")
    return candidate


def get_latest_report(
    db: Session, *, candidate_id: int, user_id: int
) -> CandidateReportResponse:
    _candidate_for_user_or_error(db, candidate_id=candidate_id, user_id=user_id)
    run = screening_runs.get_latest_completed(db, candidate_id=candidate_id)
    if run is None:
        raise ScreeningReportNotFoundError(
            "No completed screening report exists for this candidate."
        )
    return _build_report_or_error(run)


def list_screening_runs(
    db: Session, *, candidate_id: int, user_id: int
) -> list[ScreeningRunResponse]:
    _candidate_for_user_or_error(db, candidate_id=candidate_id, user_id=user_id)
    return [
        ScreeningRunResponse.model_validate(run)
        for run in screening_runs.list_for_candidate(db, candidate_id=candidate_id)
    ]


def get_screening_report(
    db: Session, *, candidate_id: int, screening_run_id: int, user_id: int
) -> CandidateReportResponse:
    _candidate_for_user_or_error(db, candidate_id=candidate_id, user_id=user_id)
    run = screening_runs.get_completed(
        db,
        candidate_id=candidate_id,
        screening_run_id=screening_run_id,
    )
    if run is None:
        raise ScreeningReportNotFoundError("Completed screening report not found")
    return _build_report_or_error(run)
