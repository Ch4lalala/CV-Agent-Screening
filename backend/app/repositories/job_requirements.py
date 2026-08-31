from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_requirement import JobRequirement
from app.schemas.job_requirement import JobRequirementCreate, JobRequirementUpdate


def create(db: Session, *, job_id: int, data: JobRequirementCreate) -> JobRequirement:
    requirement = JobRequirement(job_id=job_id, **data.model_dump())
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


def list_for_job(db: Session, *, job_id: int) -> list[JobRequirement]:
    statement = (
        select(JobRequirement)
        .where(JobRequirement.job_id == job_id)
        .order_by(JobRequirement.id)
    )
    return list(db.scalars(statement))


def get_for_job(
    db: Session, *, job_id: int, requirement_id: int
) -> JobRequirement | None:
    return db.scalar(
        select(JobRequirement).where(
            JobRequirement.id == requirement_id,
            JobRequirement.job_id == job_id,
        )
    )


def update(
    db: Session, *, requirement: JobRequirement, data: JobRequirementUpdate
) -> JobRequirement:
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(requirement, field_name, value)
    db.commit()
    db.refresh(requirement)
    return requirement


def delete(db: Session, *, requirement: JobRequirement) -> None:
    db.delete(requirement)
    db.commit()

