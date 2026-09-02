from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.candidate import CandidateCreate, CandidateUpdate


def create(db: Session, *, job_id: int, data: CandidateCreate) -> Candidate:
    candidate = Candidate(job_id=job_id, **data.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def list_for_job(db: Session, *, job_id: int) -> list[Candidate]:
    statement = (
        select(Candidate)
        .where(Candidate.job_id == job_id)
        .order_by(Candidate.id)
        .execution_options(populate_existing=True)
    )
    return list(db.scalars(statement))


def get_for_user(db: Session, *, candidate_id: int, user_id: int) -> Candidate | None:
    statement = (
        select(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .where(Candidate.id == candidate_id, Job.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    return db.scalar(statement)


def update(db: Session, *, candidate: Candidate, data: CandidateUpdate) -> Candidate:
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(candidate, field_name, value)
    db.commit()
    db.refresh(candidate)
    return candidate


def delete(db: Session, *, candidate: Candidate) -> None:
    db.delete(candidate)
    db.commit()
