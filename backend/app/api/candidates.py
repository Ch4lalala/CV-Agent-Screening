from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.models.candidate import Candidate
from app.repositories import candidates, jobs
from app.schemas.candidate import CandidateCreate, CandidateResponse, CandidateUpdate

router = APIRouter(tags=["candidates"])


def _get_job_or_404(db: DatabaseSession, user: DevelopmentUser, job_id: int) -> None:
    if jobs.get_for_user(db, job_id=job_id, user_id=user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


def _get_candidate_or_404(
    db: DatabaseSession, user: DevelopmentUser, candidate_id: int
) -> Candidate:
    candidate = candidates.get_for_user(db, candidate_id=candidate_id, user_id=user.id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


@router.post(
    "/jobs/{job_id}/candidates",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate(
    job_id: int,
    data: CandidateCreate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Candidate:
    _get_job_or_404(db, user, job_id)
    return candidates.create(db, job_id=job_id, data=data)


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateResponse])
def list_candidates(
    job_id: int, db: DatabaseSession, user: DevelopmentUser
) -> list[Candidate]:
    _get_job_or_404(db, user, job_id)
    return candidates.list_for_job(db, job_id=job_id)


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int, db: DatabaseSession, user: DevelopmentUser
) -> Candidate:
    return _get_candidate_or_404(db, user, candidate_id)


@router.patch("/candidates/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Candidate:
    candidate = _get_candidate_or_404(db, user, candidate_id)
    return candidates.update(db, candidate=candidate, data=data)


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int, db: DatabaseSession, user: DevelopmentUser
) -> Response:
    candidate = _get_candidate_or_404(db, user, candidate_id)
    candidates.delete(db, candidate=candidate)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

