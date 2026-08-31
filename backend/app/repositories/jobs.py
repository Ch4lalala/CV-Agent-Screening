from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


def create(db: Session, *, user_id: int, data: JobCreate) -> Job:
    job = Job(user_id=user_id, **data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_for_user(db: Session, *, user_id: int) -> list[Job]:
    statement = select(Job).where(Job.user_id == user_id).order_by(Job.id)
    return list(db.scalars(statement))


def get_for_user(db: Session, *, job_id: int, user_id: int) -> Job | None:
    return db.scalar(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )


def update(db: Session, *, job: Job, data: JobUpdate) -> Job:
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field_name, value)
    db.commit()
    db.refresh(job)
    return job


def delete(db: Session, *, job: Job) -> None:
    db.delete(job)
    db.commit()

