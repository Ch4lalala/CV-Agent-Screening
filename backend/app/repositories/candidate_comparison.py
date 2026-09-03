"""Fixed-query vacancy candidate coverage aggregation."""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from app.models.candidate import Candidate
from app.models.enums import (
    EvidenceStatus,
    RequirementType,
    ScreeningRunStatus,
)
from app.models.evidence_result import EvidenceResult
from app.models.resume_document import ResumeDocument
from app.models.screening_run import ScreeningRun


def list_summaries(db: Session, *, job_id: int):
    """Return every candidate with coverage from its latest completed run.

    The window subquery selects one immutable completed run per candidate. Coverage,
    resume readiness, and the optional active run are then returned in one grouped
    query, independent of the number of candidates.
    """

    ranked_completed = (
        select(
            ScreeningRun.id.label("run_id"),
            ScreeningRun.candidate_id.label("candidate_id"),
            ScreeningRun.finished_at.label("finished_at"),
            ScreeningRun.security_status.label("security_status"),
            func.row_number()
            .over(
                partition_by=ScreeningRun.candidate_id,
                order_by=(
                    func.coalesce(
                        ScreeningRun.finished_at,
                        ScreeningRun.created_at,
                    ).desc(),
                    ScreeningRun.created_at.desc(),
                    ScreeningRun.id.desc(),
                ),
            )
            .label("run_number"),
        )
        .where(ScreeningRun.status == ScreeningRunStatus.COMPLETED)
        .subquery()
    )
    latest_completed = (
        select(
            ranked_completed.c.run_id,
            ranked_completed.c.candidate_id,
            ranked_completed.c.finished_at,
            ranked_completed.c.security_status,
        )
        .where(ranked_completed.c.run_number == 1)
        .subquery()
    )
    active_run = aliased(ScreeningRun)

    def count_result(requirement_type: RequirementType, status: EvidenceStatus):
        return func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            EvidenceResult.requirement_type == requirement_type,
                            EvidenceResult.status == status,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        )

    required_supported = count_result(
        RequirementType.REQUIRED, EvidenceStatus.SUPPORTED
    )
    required_partial = count_result(RequirementType.REQUIRED, EvidenceStatus.PARTIAL)
    required_no_evidence = count_result(
        RequirementType.REQUIRED, EvidenceStatus.NO_EVIDENCE
    )
    preferred_supported = count_result(
        RequirementType.PREFERRED, EvidenceStatus.SUPPORTED
    )
    preferred_partial = count_result(
        RequirementType.PREFERRED, EvidenceStatus.PARTIAL
    )
    preferred_no_evidence = count_result(
        RequirementType.PREFERRED, EvidenceStatus.NO_EVIDENCE
    )

    statement = (
        select(
            Candidate.id.label("candidate_id"),
            Candidate.name,
            Candidate.email,
            Candidate.original_filename,
            Candidate.status,
            Candidate.created_at,
            ResumeDocument.extraction_status.label("resume_extraction_status"),
            latest_completed.c.run_id.label("latest_completed_run_id"),
            latest_completed.c.finished_at.label("latest_completed_at"),
            latest_completed.c.security_status.label("security_status"),
            active_run.id.label("active_screening_run_id"),
            active_run.current_stage.label("active_screening_stage"),
            active_run.current_stage_updated_at.label(
                "active_screening_stage_updated_at"
            ),
            required_supported.label("required_supported"),
            required_partial.label("required_partial"),
            required_no_evidence.label("required_no_evidence"),
            preferred_supported.label("preferred_supported"),
            preferred_partial.label("preferred_partial"),
            preferred_no_evidence.label("preferred_no_evidence"),
            func.coalesce(
                func.sum(
                    case(
                        (EvidenceResult.needs_human_verification.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("needs_verification_count"),
        )
        .outerjoin(
            ResumeDocument,
            ResumeDocument.candidate_id == Candidate.id,
        )
        .outerjoin(
            latest_completed,
            latest_completed.c.candidate_id == Candidate.id,
        )
        .outerjoin(
            EvidenceResult,
            EvidenceResult.screening_run_id == latest_completed.c.run_id,
        )
        .outerjoin(
            active_run,
            and_(
                active_run.candidate_id == Candidate.id,
                active_run.status == ScreeningRunStatus.PROCESSING,
            ),
        )
        .where(Candidate.job_id == job_id)
        .group_by(
            Candidate.id,
            ResumeDocument.extraction_status,
            latest_completed.c.run_id,
            latest_completed.c.finished_at,
            latest_completed.c.security_status,
            active_run.id,
            active_run.current_stage,
            active_run.current_stage_updated_at,
        )
    )
    return db.execute(statement).mappings().all()
