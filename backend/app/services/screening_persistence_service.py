"""Atomic persistence and reconstruction for immutable screening reports."""

from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.schemas import CandidateProfile as CandidateProfileSchema
from app.agents.schemas import ScreeningReport
from app.models.candidate_profile import CandidateProfile as CandidateProfileRecord
from app.models.enums import (
    CandidateStatus,
    EvidenceConfidence,
    EvidenceStatus,
    RequirementType,
    ScreeningRunStatus,
)
from app.models.evidence_item import EvidenceItem
from app.models.evidence_result import EvidenceResult
from app.models.interview_question import InterviewQuestion
from app.models.screening_run import ScreeningRun
from app.repositories import screening_runs
from app.schemas.screening import (
    CandidateReportCandidateResponse,
    CandidateReportResponse,
    EvidenceItemResponse,
    EvidenceResultResponse,
    InterviewQuestionResponse,
    ScreeningCoverageResponse,
    ScreeningRunResponse,
)


class ScreeningPersistenceError(Exception):
    pass


def persist_completed_report(
    db: Session,
    *,
    run: ScreeningRun,
    report: ScreeningReport,
    valid_requirement_ids: set[int],
) -> ScreeningRun:
    """Persist normalized rows and the source report in one transaction."""

    try:
        if run.status != ScreeningRunStatus.PROCESSING or run.report_json is not None:
            raise ScreeningPersistenceError("Screening run is not writable")

        db.add(
            CandidateProfileRecord(
                screening_run_id=run.id,
                profile_json=report.candidate_profile.model_dump(mode="json"),
            )
        )

        for assessment in report.evidence_results:
            requirement_id = assessment.source_requirement_id
            if requirement_id not in valid_requirement_ids:
                requirement_id = None
            evidence_result = EvidenceResult(
                screening_run_id=run.id,
                requirement_id=requirement_id,
                requirement_name=assessment.requirement,
                requirement_type=RequirementType(assessment.requirement_type),
                status=EvidenceStatus(assessment.status),
                confidence=EvidenceConfidence(assessment.confidence),
                explanation=assessment.explanation,
                needs_human_verification=assessment.needs_human_verification,
            )
            evidence_result.evidence_items = [
                EvidenceItem(
                    quote=item.quote,
                    source_section=item.source_section,
                    source_page=item.source_page,
                )
                for item in assessment.evidence
            ]
            db.add(evidence_result)

        db.add_all(
            [
                InterviewQuestion(
                    screening_run_id=run.id,
                    requirement_name=item.requirement,
                    question=item.question,
                )
                for item in report.interview_questions
            ]
        )

        run.report_json = report.model_dump(mode="json")
        run.status = ScreeningRunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        run.error_message = None

        if screening_runs.latest_run_id(db, candidate_id=run.candidate_id) == run.id:
            run.candidate.status = CandidateStatus.COMPLETED

        db.commit()
    except ScreeningPersistenceError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise ScreeningPersistenceError("Unable to persist screening report") from exc

    completed = screening_runs.get_completed(
        db,
        candidate_id=run.candidate_id,
        screening_run_id=run.id,
    )
    if completed is None:
        raise ScreeningPersistenceError("Persisted screening report was not found")
    return completed


def mark_failed(
    db: Session, *, run_id: int, candidate_id: int, error_message: str
) -> None:
    run = db.get(ScreeningRun, run_id)
    if run is None or run.status != ScreeningRunStatus.PROCESSING:
        return

    run.status = ScreeningRunStatus.FAILED
    run.finished_at = datetime.now(UTC)
    run.error_message = error_message
    if screening_runs.latest_run_id(db, candidate_id=candidate_id) == run.id:
        run.candidate.status = CandidateStatus.FAILED
    db.commit()


def build_candidate_report(run: ScreeningRun) -> CandidateReportResponse:
    if (
        run.status != ScreeningRunStatus.COMPLETED
        or run.report_json is None
        or run.candidate_profile is None
    ):
        raise ScreeningPersistenceError("Completed screening report is incomplete")

    try:
        snapshot = ScreeningReport.model_validate(run.report_json)
        profile = CandidateProfileSchema.model_validate(
            run.candidate_profile.profile_json
        )
    except ValidationError as exc:
        raise ScreeningPersistenceError("Stored screening report is invalid") from exc

    evidence_results = [
        EvidenceResultResponse(
            id=result.id,
            requirement_id=result.requirement_id,
            requirement_name=result.requirement_name,
            requirement_type=result.requirement_type,
            status=result.status,
            confidence=result.confidence,
            explanation=result.explanation,
            needs_human_verification=result.needs_human_verification,
            evidence_items=[
                EvidenceItemResponse.model_validate(item)
                for item in sorted(result.evidence_items, key=lambda value: value.id)
            ],
            created_at=result.created_at,
        )
        for result in sorted(run.evidence_results, key=lambda value: value.id)
    ]
    questions = [
        InterviewQuestionResponse.model_validate(item)
        for item in sorted(run.interview_questions, key=lambda value: value.id)
    ]

    return CandidateReportResponse(
        screening_run=ScreeningRunResponse.model_validate(run),
        candidate=CandidateReportCandidateResponse.model_validate(run.candidate),
        job_title=snapshot.job_title,
        normalized_requirements=snapshot.normalized_requirements,
        candidate_profile=profile,
        coverage=ScreeningCoverageResponse(
            required=snapshot.required_coverage,
            preferred=snapshot.preferred_coverage,
        ),
        evidence_results=evidence_results,
        needs_verification=snapshot.needs_verification,
        interview_questions=questions,
        security_warning=None,
    )
