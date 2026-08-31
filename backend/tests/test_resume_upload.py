from pathlib import Path
from uuid import UUID

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Candidate, ResumeDocument
from app.models.enums import ResumeExtractionStatus
from tests.test_jobs import create_job


def make_pdf(*page_texts: str | None) -> bytes:
    document = fitz.open()
    for text in page_texts or (None,):
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def upload_resume(
    client: TestClient,
    job_id: int,
    pdf_bytes: bytes,
    *,
    filename: str = "resume.pdf",
    content_type: str = "application/pdf",
    data: dict[str, str] | None = None,
):
    return client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        files={"file": (filename, pdf_bytes, content_type)},
        data=data or {},
    )


def test_valid_pdf_upload_extracts_and_persists_without_exposing_text(
    client: TestClient,
    db_session: Session,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]
    response = upload_resume(
        client,
        job_id,
        make_pdf("Backend engineer with PostgreSQL experience.", "Built REST APIs."),
        data={"name": "Synthetic Candidate", "email": "resume@example.com"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Synthetic Candidate"
    assert body["email"] == "resume@example.com"
    assert body["status"] == "uploaded"
    assert body["original_filename"] == "resume.pdf"
    assert body["resume"]["page_count"] == 2
    assert body["resume"]["extraction_status"] == "completed"
    assert body["resume"]["text_length"] > 0
    assert "extracted_text" not in body
    assert "resume_path" not in body

    candidate = db_session.get(Candidate, body["id"])
    assert candidate is not None
    assert candidate.resume_path is not None
    assert UUID(Path(candidate.resume_path).stem)
    assert (resume_storage_path / candidate.resume_path).is_file()

    resume = db_session.scalar(
        select(ResumeDocument).where(ResumeDocument.candidate_id == candidate.id)
    )
    assert resume is not None
    assert resume.extraction_status is ResumeExtractionStatus.COMPLETED
    assert "PostgreSQL experience" in (resume.extracted_text or "")
    assert "Built REST APIs" in (resume.extracted_text or "")

    metadata = client.get(f"/api/v1/candidates/{candidate.id}/resume")
    assert metadata.status_code == 200
    assert metadata.json() == {
        "original_filename": "resume.pdf",
        "page_count": 2,
        "extraction_status": "completed",
        "text_length": len(resume.extracted_text or ""),
        "message": None,
    }


def test_upload_allows_missing_name_and_email(client: TestClient) -> None:
    job_id = create_job(client)["id"]
    response = upload_resume(client, job_id, make_pdf("Text-based resume"))

    assert response.status_code == 201
    assert response.json()["name"] is None
    assert response.json()["email"] is None


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "expected_detail"),
    [
        ("resume.pdf", "text/plain", make_pdf("Resume"), "MIME type"),
        ("resume.txt", "application/pdf", make_pdf("Resume"), "Unsupported file format"),
        ("resume.pdf", "application/pdf", b"not a pdf", "signature"),
        ("resume.pdf", "application/pdf", b"PK\x03\x04fake zip", "signature"),
    ],
)
def test_invalid_files_are_rejected(
    client: TestClient,
    resume_storage_path: Path,
    filename: str,
    content_type: str,
    content: bytes,
    expected_detail: str,
) -> None:
    job_id = create_job(client)["id"]
    response = upload_resume(
        client,
        job_id,
        content,
        filename=filename,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert expected_detail in response.json()["detail"]
    assert not list(resume_storage_path.glob("*"))


def test_oversized_pdf_is_rejected_and_cleaned_up(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    resume_storage_path: Path,
) -> None:
    monkeypatch.setenv("MAX_CV_SIZE_MB", "0.00001")
    job_id = create_job(client)["id"]

    response = upload_resume(client, job_id, make_pdf("Too large for test limit"))

    assert response.status_code == 413
    assert "exceeds allowed size" in response.json()["detail"]
    assert not list(resume_storage_path.glob("*"))


def test_upload_to_missing_job_does_not_store_file(
    client: TestClient, resume_storage_path: Path
) -> None:
    response = upload_resume(client, 9999, make_pdf("Resume"))

    assert response.status_code == 404
    assert not resume_storage_path.exists()


def test_candidate_delete_removes_resume_record_and_file(
    client: TestClient,
    db_session: Session,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]
    upload = upload_resume(client, job_id, make_pdf("Disposable resume"))
    candidate_id = upload.json()["id"]
    candidate = db_session.get(Candidate, candidate_id)
    assert candidate is not None and candidate.resume_path is not None
    stored_path = resume_storage_path / candidate.resume_path
    resume_id = candidate.resume_document.id
    assert stored_path.exists()

    response = client.delete(f"/api/v1/candidates/{candidate_id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Candidate, candidate_id) is None
    assert db_session.get(ResumeDocument, resume_id) is None
    assert not stored_path.exists()


def test_empty_pdf_is_persisted_with_clear_extraction_failure(
    client: TestClient, db_session: Session
) -> None:
    job_id = create_job(client)["id"]
    response = upload_resume(client, job_id, make_pdf(None))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["resume"]["extraction_status"] == "failed"
    assert body["resume"]["text_length"] == 0
    assert "text-based resume" in body["resume"]["message"]

    resume = db_session.scalar(
        select(ResumeDocument).where(ResumeDocument.candidate_id == body["id"])
    )
    assert resume is not None
    assert resume.extraction_status is ResumeExtractionStatus.FAILED


def test_malicious_original_filename_is_sanitized(
    client: TestClient, db_session: Session, resume_storage_path: Path
) -> None:
    job_id = create_job(client)["id"]
    response = upload_resume(
        client,
        job_id,
        make_pdf("Safe storage"),
        filename="../../resume.pdf",
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "resume.pdf"
    candidate = db_session.get(Candidate, response.json()["id"])
    assert candidate is not None and candidate.resume_path is not None
    stored_path = (resume_storage_path / candidate.resume_path).resolve()
    assert stored_path.parent == resume_storage_path.resolve()
    assert stored_path.is_file()


def test_duplicate_original_filenames_use_distinct_internal_files(
    client: TestClient, db_session: Session, resume_storage_path: Path
) -> None:
    job_id = create_job(client)["id"]
    first = upload_resume(client, job_id, make_pdf("First"), filename="resume.pdf")
    second = upload_resume(client, job_id, make_pdf("Second"), filename="resume.pdf")

    assert first.status_code == second.status_code == 201
    first_candidate = db_session.get(Candidate, first.json()["id"])
    second_candidate = db_session.get(Candidate, second.json()["id"])
    assert first_candidate is not None and second_candidate is not None
    assert first_candidate.resume_path != second_candidate.resume_path
    assert len(list(resume_storage_path.glob("*.pdf"))) == 2


def test_database_failure_cleans_up_saved_file(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]

    def fail_commit() -> None:
        raise SQLAlchemyError("synthetic persistence failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    response = upload_resume(client, job_id, make_pdf("Orphan cleanup test"))

    assert response.status_code == 500
    assert not list(resume_storage_path.glob("*"))


def test_candidate_delete_never_follows_untrusted_database_path(
    client: TestClient,
    db_session: Session,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]
    created = client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        json={"name": "Candidate", "email": "candidate@example.com"},
    )
    candidate = db_session.get(Candidate, created.json()["id"])
    assert candidate is not None
    candidate.resume_path = "../outside.pdf"
    db_session.commit()
    outside_file = resume_storage_path.parent / "outside.pdf"
    outside_file.write_bytes(b"must not be deleted")

    response = client.delete(f"/api/v1/candidates/{candidate.id}")

    assert response.status_code == 204
    assert outside_file.read_bytes() == b"must not be deleted"


def test_job_delete_removes_candidate_resume_files(
    client: TestClient,
    db_session: Session,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]
    first = upload_resume(client, job_id, make_pdf("First resume"))
    second = upload_resume(client, job_id, make_pdf("Second resume"))
    candidates = [
        db_session.get(Candidate, first.json()["id"]),
        db_session.get(Candidate, second.json()["id"]),
    ]
    stored_paths = [
        resume_storage_path / candidate.resume_path
        for candidate in candidates
        if candidate is not None and candidate.resume_path is not None
    ]
    assert len(stored_paths) == 2
    assert all(path.exists() for path in stored_paths)

    response = client.delete(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 204
    assert all(not path.exists() for path in stored_paths)


def test_candidate_delete_succeeds_when_resume_file_is_already_missing(
    client: TestClient,
    db_session: Session,
    resume_storage_path: Path,
) -> None:
    job_id = create_job(client)["id"]
    uploaded = upload_resume(client, job_id, make_pdf("Missing file test"))
    candidate_id = uploaded.json()["id"]
    candidate = db_session.get(Candidate, candidate_id)
    assert candidate is not None and candidate.resume_path is not None
    (resume_storage_path / candidate.resume_path).unlink()

    response = client.delete(f"/api/v1/candidates/{candidate_id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Candidate, candidate_id) is None
