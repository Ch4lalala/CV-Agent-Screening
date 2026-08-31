from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Candidate, JobRequirement, User
from app.schemas.user import UserResponse
from tests.test_jobs import create_job


def test_job_delete_cascades_to_children_but_not_user(
    client: TestClient, db_session: Session, development_user: User
) -> None:
    job_id = create_job(client)["id"]
    requirement = client.post(
        f"/api/v1/jobs/{job_id}/requirements",
        json={"name": "Go"},
    )
    candidate = client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        json={"name": "Candidate", "email": "candidate@example.com"},
    )
    assert requirement.status_code == 201
    assert candidate.status_code == 201

    assert client.delete(f"/api/v1/jobs/{job_id}").status_code == 204
    assert db_session.scalar(select(func.count()).select_from(JobRequirement)) == 0
    assert db_session.scalar(select(func.count()).select_from(Candidate)) == 0
    assert db_session.get(User, development_user.id) is not None


def test_user_response_never_contains_password_hash(development_user: User) -> None:
    response = UserResponse.model_validate(development_user).model_dump(mode="json")
    assert "password_hash" not in response
