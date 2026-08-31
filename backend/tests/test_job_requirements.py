from fastapi.testclient import TestClient

from tests.test_jobs import create_job


def test_requirement_create_list_update_delete(client: TestClient) -> None:
    job_id = create_job(client)["id"]
    created = client.post(
        f"/api/v1/jobs/{job_id}/requirements",
        json={
            "name": "PostgreSQL",
            "description": "Relational database experience",
            "requirement_type": "required",
            "priority": 1,
        },
    )
    assert created.status_code == 201
    requirement_id = created.json()["id"]

    listed = client.get(f"/api/v1/jobs/{job_id}/requirements")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [requirement_id]

    updated = client.patch(
        f"/api/v1/jobs/{job_id}/requirements/{requirement_id}",
        json={"requirement_type": "preferred", "priority": None},
    )
    assert updated.status_code == 200
    assert updated.json()["requirement_type"] == "preferred"
    assert updated.json()["priority"] is None

    deleted = client.delete(
        f"/api/v1/jobs/{job_id}/requirements/{requirement_id}"
    )
    assert deleted.status_code == 204
    assert client.patch(
        f"/api/v1/jobs/{job_id}/requirements/{requirement_id}",
        json={"name": "Missing"},
    ).status_code == 404


def test_requirement_rejects_invalid_job(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs/9999/requirements",
        json={"name": "Go", "requirement_type": "required"},
    )
    assert response.status_code == 404

