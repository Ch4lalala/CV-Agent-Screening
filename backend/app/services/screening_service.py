"""Coordinate screening initiation, background graph execution, and report reads."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
from app.models.enums import (
    CandidateStatus,
    ResumeExtractionStatus,
    ScreeningRunStatus,
    ScreeningStage,
)
from app.models.screening_run import ScreeningRun
from app.repositories import (
    candidates,
    job_requirements,
    jobs,
    resume_documents,
    screening_runs,
)
from app.schemas.screening import (
    CandidateReportResponse,
    ScreeningRunResponse,
    ScreeningStartResponse,
)
from app.services import screening_persistence_service

logger = logging.getLogger(__name__)

_NODE_STAGES = (
    ScreeningStage.NORMALIZE_REQUIREMENTS,
    ScreeningStage.EXTRACT_CANDIDATE_PROFILE,
    ScreeningStage.MATCH_EVIDENCE,
    ScreeningStage.ANALYZE_UNCERTAINTY,
    ScreeningStage.GENERATE_INTERVIEW_QUESTIONS,
    ScreeningStage.GENERATE_REPORT,
)
_NEXT_STAGE = {
    stage.value: _NODE_STAGES[index + 1]
    for index, stage in enumerate(_NODE_STAGES[:-1])
}
_background_tasks: set[asyncio.Task[None]] = set()


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


@dataclass(frozen=True)
class ScreeningExecutionContext:
    run_id: int
    candidate_id: int
    initial_state: RecruitmentState
    valid_requirement_ids: set[int]


def _safe_failure_message(exc: BaseException) -> str:
    if isinstance(exc, AIConfigurationError):
        return "AI service is not configured."
    if isinstance(exc, AIProviderError):
        return "AI provider is temporarily unavailable."
    if isinstance(exc, AIStructuredOutputError):
        return "AI returned an invalid structured response."
    if isinstance(exc, asyncio.CancelledError):
        return "Candidate screening was interrupted."
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
        current_stage=ScreeningStage.QUEUED,
        current_stage_updated_at=datetime.now(UTC),
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


def start_candidate_screening(
    db: Session, *, candidate_id: int, user_id: int
) -> tuple[ScreeningStartResponse, ScreeningExecutionContext]:
    """Commit the authoritative processing run before any graph work begins."""

    run, initial_state, valid_requirement_ids = _start_screening(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    context = ScreeningExecutionContext(
        run_id=run.id,
        candidate_id=candidate_id,
        initial_state=initial_state,
        valid_requirement_ids=valid_requirement_ids,
    )
    logger.info(
        "screening_queued",
        extra={
            "candidate_id": candidate_id,
            "job_id": initial_state["job_id"],
            "screening_run_id": run.id,
        },
    )
    return (
        ScreeningStartResponse(
            screening_run_id=run.id,
            candidate_id=candidate_id,
            status=run.status,
            current_stage=run.current_stage,
        ),
        context,
    )


def _persist_stage(db: Session, *, run_id: int, stage: ScreeningStage) -> None:
    run = db.get(ScreeningRun, run_id)
    if run is None or run.status != ScreeningRunStatus.PROCESSING:
        raise ScreeningExecutionError("Screening run is no longer processing")
    run.current_stage = stage
    run.current_stage_updated_at = datetime.now(UTC)
    db.commit()


async def _stream_graph(
    graph: object,
    *,
    initial_state: RecruitmentState,
    on_node_completed: Callable[[str], Awaitable[None]],
) -> object:
    """Return the final report payload while reporting real completed nodes."""

    stream = getattr(graph, "astream", None)
    if callable(stream):
        final_report: object | None = None
        async for update in stream(initial_state, stream_mode="updates"):
            if not isinstance(update, dict):
                continue
            for node_name, node_update in update.items():
                if node_name not in {stage.value for stage in _NODE_STAGES}:
                    continue
                if (
                    node_name == ScreeningStage.GENERATE_REPORT.value
                    and isinstance(node_update, dict)
                ):
                    final_report = node_update.get("final_report")
                await on_node_completed(node_name)
        if final_report is None:
            raise ScreeningExecutionError("Screening graph did not produce a report")
        return final_report

    invoke = getattr(graph, "ainvoke", None)
    if not callable(invoke):
        raise ScreeningExecutionError("Screening graph is not executable")
    result = await invoke(initial_state)
    if not isinstance(result, dict) or "final_report" not in result:
        raise ScreeningExecutionError("Screening graph did not produce a report")
    return result["final_report"]


async def execute_screening(
    db: Session,
    *,
    context: ScreeningExecutionContext,
    graph: object | None = None,
) -> CandidateReportResponse:
    """Execute LangGraph outside the request lifecycle and persist real node progress."""

    _persist_stage(
        db,
        run_id=context.run_id,
        stage=ScreeningStage.NORMALIZE_REQUIREMENTS,
    )

    async def node_completed(node_name: str) -> None:
        next_stage = _NEXT_STAGE.get(node_name)
        if next_stage is not None:
            _persist_stage(db, run_id=context.run_id, stage=next_stage)

    try:
        screening_graph = graph or get_recruitment_graph()
        report_payload = await _stream_graph(
            screening_graph,
            initial_state=context.initial_state,
            on_node_completed=node_completed,
        )
        report = ScreeningReport.model_validate(report_payload)
        run = db.get(ScreeningRun, context.run_id)
        if run is None:
            raise ScreeningExecutionError("Screening run was not found")
        completed_run = screening_persistence_service.persist_completed_report(
            db,
            run=run,
            report=report,
            valid_requirement_ids=context.valid_requirement_ids,
        )
    except asyncio.CancelledError as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise
    except (AIConfigurationError, AIProviderError, AIStructuredOutputError) as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise
    except (KeyError, TypeError, ValidationError) as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise ScreeningExecutionError("Candidate screening failed") from exc
    except screening_persistence_service.ScreeningPersistenceError as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise ScreeningExecutionError("Candidate screening failed") from exc
    except ScreeningExecutionError as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise
    except Exception as exc:
        _record_failed_run(
            db,
            run_id=context.run_id,
            candidate_id=context.candidate_id,
            exc=exc,
        )
        raise ScreeningExecutionError("Candidate screening failed") from exc

    logger.info(
        "screening_completed",
        extra={
            "candidate_id": context.candidate_id,
            "screening_run_id": context.run_id,
        },
    )
    return _build_report_or_error(completed_run)


async def screen_candidate(
    db: Session,
    *,
    candidate_id: int,
    user_id: int,
    graph: object | None = None,
) -> CandidateReportResponse:
    """Synchronous service helper retained for deterministic service-level tests."""

    _, context = start_candidate_screening(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    return await execute_screening(db, context=context, graph=graph)


async def _background_screening(
    context: ScreeningExecutionContext,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        try:
            await execute_screening(db, context=context)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Safe failure state and structured metadata are already persisted.
            return


def _discard_background_task(task: asyncio.Task[None]) -> None:
    _background_tasks.discard(task)
    if task.cancelled():
        return
    try:
        task.result()
    except Exception:
        logger.exception("Unexpected unhandled background screening failure")


def schedule_screening(
    context: ScreeningExecutionContext,
    *,
    bind: Engine | Connection,
) -> None:
    """Keep a strong task reference while an in-process screening is active."""

    session_factory = sessionmaker(
        bind=bind,
        autoflush=False,
        expire_on_commit=False,
    )
    task = asyncio.create_task(_background_screening(context, session_factory))
    _background_tasks.add(task)
    task.add_done_callback(_discard_background_task)


def _record_failed_run(
    db: Session,
    *,
    run_id: int,
    candidate_id: int,
    exc: BaseException,
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


def get_screening_result(
    db: Session, *, candidate_id: int, screening_run_id: int, user_id: int
) -> ScreeningRunResponse | CandidateReportResponse:
    _candidate_for_user_or_error(db, candidate_id=candidate_id, user_id=user_id)
    run = screening_runs.get_for_candidate(
        db,
        candidate_id=candidate_id,
        screening_run_id=screening_run_id,
    )
    if run is None:
        raise ScreeningReportNotFoundError("Screening run not found")
    if run.status != ScreeningRunStatus.COMPLETED:
        return ScreeningRunResponse.model_validate(run)
    completed = screening_runs.get_completed(
        db,
        candidate_id=candidate_id,
        screening_run_id=screening_run_id,
    )
    if completed is None:
        raise ScreeningExecutionError("Completed screening report is incomplete")
    return _build_report_or_error(completed)


def get_screening_report(
    db: Session, *, candidate_id: int, screening_run_id: int, user_id: int
) -> CandidateReportResponse:
    result = get_screening_result(
        db,
        candidate_id=candidate_id,
        screening_run_id=screening_run_id,
        user_id=user_id,
    )
    if isinstance(result, ScreeningRunResponse):
        raise ScreeningReportNotFoundError("Completed screening report not found")
    return result
