from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.candidate import Candidate
from app.models.evidence_result import EvidenceResult
from app.models.job import Job
from app.models.screening_run import ScreeningRun
from app.models.enums import ScreeningRunStatus


def candidate_for_user_for_update(
    db: Session, *, candidate_id: int, user_id: int
) -> Candidate | None:
    statement = (
        select(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .where(Candidate.id == candidate_id, Job.user_id == user_id)
        .with_for_update()
    )
    return db.scalar(statement)


def has_processing_run(db: Session, *, candidate_id: int) -> bool:
    statement = select(ScreeningRun.id).where(
        ScreeningRun.candidate_id == candidate_id,
        ScreeningRun.status == ScreeningRunStatus.PROCESSING,
    )
    return db.scalar(statement) is not None


def latest_run_id(db: Session, *, candidate_id: int) -> int | None:
    statement = (
        select(ScreeningRun.id)
        .where(ScreeningRun.candidate_id == candidate_id)
        .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def list_for_candidate(db: Session, *, candidate_id: int) -> list[ScreeningRun]:
    statement = (
        select(ScreeningRun)
        .where(ScreeningRun.candidate_id == candidate_id)
        .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
        .execution_options(populate_existing=True)
    )
    return list(db.scalars(statement))


def get_for_candidate(
    db: Session, *, candidate_id: int, screening_run_id: int
) -> ScreeningRun | None:
    return db.scalar(
        select(ScreeningRun)
        .where(
            ScreeningRun.id == screening_run_id,
            ScreeningRun.candidate_id == candidate_id,
        )
        .execution_options(populate_existing=True)
    )


def get_completed(
    db: Session, *, candidate_id: int, screening_run_id: int
) -> ScreeningRun | None:
    statement = (
        select(ScreeningRun)
        .where(
            ScreeningRun.id == screening_run_id,
            ScreeningRun.candidate_id == candidate_id,
            ScreeningRun.status == ScreeningRunStatus.COMPLETED,
        )
        .options(
            selectinload(ScreeningRun.candidate),
            selectinload(ScreeningRun.candidate_profile),
            selectinload(ScreeningRun.evidence_results).selectinload(
                EvidenceResult.evidence_items
            ),
            selectinload(ScreeningRun.interview_questions),
        )
        .execution_options(populate_existing=True)
    )
    return db.scalar(statement)


def get_latest_completed(db: Session, *, candidate_id: int) -> ScreeningRun | None:
    run_id = db.scalar(
        select(ScreeningRun.id)
        .where(
            ScreeningRun.candidate_id == candidate_id,
            ScreeningRun.status == ScreeningRunStatus.COMPLETED,
        )
        .order_by(ScreeningRun.created_at.desc(), ScreeningRun.id.desc())
        .limit(1)
    )
    if run_id is None:
        return None
    return get_completed(db, candidate_id=candidate_id, screening_run_id=run_id)
