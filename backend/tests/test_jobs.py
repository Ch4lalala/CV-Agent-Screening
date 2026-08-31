from fastapi.testclient import TestClient


def create_job(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/jobs",
        json={
            "title": "Backend Engineer Intern",
            "description": "Build small, reliable APIs.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_job_create_list_get_update_delete(client: TestClient) -> None:
    created = create_job(client)
    job_id = created["id"]
    assert created["status"] == "draft"
    assert "password_hash" not in created

    listed = client.get("/api/v1/jobs")
    assert listed.status_code == 200
    assert [job["id"] for job in listed.json()] == [job_id]

    fetched = client.get(f"/api/v1/jobs/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Backend Engineer Intern"

    updated = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Backend Engineer", "status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Backend Engineer"
    assert updated.json()["status"] == "active"

    deleted = client.delete(f"/api/v1/jobs/{job_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/jobs/{job_id}").status_code == 404


def test_job_not_found_and_invalid_data(client: TestClient) -> None:
    assert client.get("/api/v1/jobs/9999").status_code == 404

    invalid = client.post(
        "/api/v1/jobs",
        json={"title": "", "description": "Valid", "status": "unknown"},
    )
    assert invalid.status_code == 422

