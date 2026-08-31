from fastapi.testclient import TestClient

from tests.test_jobs import create_job


def test_candidate_create_list_get_update_delete(client: TestClient) -> None:
    job_id = create_job(client)["id"]
    created = client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        json={"name": "Synthetic Candidate", "email": "candidate@example.com"},
    )
    assert created.status_code == 201
    candidate = created.json()
    candidate_id = candidate["id"]
    assert candidate["status"] == "uploaded"
    assert candidate["original_filename"] is None
    assert candidate["resume_path"] is None

    listed = client.get(f"/api/v1/jobs/{job_id}/candidates")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [candidate_id]

    fetched = client.get(f"/api/v1/candidates/{candidate_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "candidate@example.com"

    updated = client.patch(
        f"/api/v1/candidates/{candidate_id}",
        json={"name": "Updated Candidate", "status": "processing"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Candidate"
    assert updated.json()["status"] == "processing"

    deleted = client.delete(f"/api/v1/candidates/{candidate_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/candidates/{candidate_id}").status_code == 404


def test_candidate_not_found_invalid_job_and_validation(client: TestClient) -> None:
    assert client.get("/api/v1/candidates/9999").status_code == 404
    assert client.post(
        "/api/v1/jobs/9999/candidates",
        json={"name": "Candidate", "email": "candidate@example.com"},
    ).status_code == 404

    job_id = create_job(client)["id"]
    invalid = client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        json={"name": "Candidate", "email": "not-an-email"},
    )
    assert invalid.status_code == 422
