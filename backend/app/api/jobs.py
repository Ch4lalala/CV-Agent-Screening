from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.repositories import job_requirements, jobs
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.schemas.job_requirement import (
    JobRequirementCreate,
    JobRequirementResponse,
    JobRequirementUpdate,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_job_or_404(db: DatabaseSession, user: DevelopmentUser, job_id: int) -> Job:
    job = jobs.get_for_user(db, job_id=job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _get_requirement_or_404(
    db: DatabaseSession, job_id: int, requirement_id: int
) -> JobRequirement:
    requirement = job_requirements.get_for_job(
        db, job_id=job_id, requirement_id=requirement_id
    )
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job requirement not found",
        )
    return requirement


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, db: DatabaseSession, user: DevelopmentUser) -> Job:
    return jobs.create(db, user_id=user.id, data=data)


@router.get("", response_model=list[JobResponse])
def list_jobs(db: DatabaseSession, user: DevelopmentUser) -> list[Job]:
    return jobs.list_for_user(db, user_id=user.id)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: DatabaseSession, user: DevelopmentUser) -> Job:
    return _get_job_or_404(db, user, job_id)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int, data: JobUpdate, db: DatabaseSession, user: DevelopmentUser
) -> Job:
    job = _get_job_or_404(db, user, job_id)
    return jobs.update(db, job=job, data=data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: DatabaseSession, user: DevelopmentUser) -> Response:
    job = _get_job_or_404(db, user, job_id)
    jobs.delete(db, job=job)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{job_id}/requirements",
    response_model=JobRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    job_id: int,
    data: JobRequirementCreate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> JobRequirement:
    _get_job_or_404(db, user, job_id)
    return job_requirements.create(db, job_id=job_id, data=data)


@router.get("/{job_id}/requirements", response_model=list[JobRequirementResponse])
def list_requirements(
    job_id: int, db: DatabaseSession, user: DevelopmentUser
) -> list[JobRequirement]:
    _get_job_or_404(db, user, job_id)
    return job_requirements.list_for_job(db, job_id=job_id)


@router.patch(
    "/{job_id}/requirements/{requirement_id}",
    response_model=JobRequirementResponse,
)
def update_requirement(
    job_id: int,
    requirement_id: int,
    data: JobRequirementUpdate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> JobRequirement:
    _get_job_or_404(db, user, job_id)
    requirement = _get_requirement_or_404(db, job_id, requirement_id)
    return job_requirements.update(db, requirement=requirement, data=data)


@router.delete(
    "/{job_id}/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_requirement(
    job_id: int,
    requirement_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Response:
    _get_job_or_404(db, user, job_id)
    requirement = _get_requirement_or_404(db, job_id, requirement_id)
    job_requirements.delete(db, requirement=requirement)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

