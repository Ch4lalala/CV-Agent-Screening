from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session

from app.models import Candidate, EvidenceResult, Job, ResumeDocument, ScreeningRun, User
from app.models.enums import (
    CandidateStatus,
    EvidenceConfidence,
    EvidenceStatus,
    RequirementType,
    ResumeExtractionStatus,
    ScreeningRunStatus,
    ScreeningStage,
)


NOW = datetime(2026, 9, 2, 5, 0, tzinfo=UTC)


def make_job(db: Session, user: User, title: str = "Backend Engineer") -> Job:
    job = Job(user_id=user.id, title=title, description="Build backend services.")
    db.add(job)
    db.flush()
    return job


def make_candidate(
    db: Session,
    job: Job,
    name: str,
    *,
    status: CandidateStatus = CandidateStatus.COMPLETED,
    created_offset: int = 0,
) -> Candidate:
    candidate = Candidate(
        job_id=job.id,
        name=name,
        email=f"{name.lower().replace(' ', '-')}@example.com",
        original_filename=f"{name}.pdf",
        resume_path=f"/private/{name}.pdf",
        status=status,
        created_at=NOW + timedelta(minutes=created_offset),
    )
    db.add(candidate)
    db.flush()
    db.add(
        ResumeDocument(
            candidate_id=candidate.id,
            extracted_text=f"PRIVATE RAW RESUME TEXT FOR {name}",
            page_count=1,
            extraction_status=ResumeExtractionStatus.COMPLETED,
        )
    )
    return candidate


def add_completed_run(
    db: Session,
    candidate: Candidate,
    *,
    required: tuple[int, int, int],
    preferred: tuple[int, int, int] = (0, 0, 0),
    verification_count: int = 0,
    finished_offset: int = 0,
) -> ScreeningRun:
    finished_at = NOW + timedelta(minutes=finished_offset)
    run = ScreeningRun(
        candidate_id=candidate.id,
        status=ScreeningRunStatus.COMPLETED,
        current_stage=ScreeningStage.COMPLETED,
        started_at=finished_at - timedelta(seconds=5),
        finished_at=finished_at,
        model_name="deterministic-test-model",
        report_json={"immutable": True, "offset": finished_offset},
        created_at=finished_at,
    )
    db.add(run)
    db.flush()

    remaining_verifications = verification_count
    for requirement_type, counts in (
        (RequirementType.REQUIRED, required),
        (RequirementType.PREFERRED, preferred),
    ):
        for result_status, count in zip(
            (
                EvidenceStatus.SUPPORTED,
                EvidenceStatus.PARTIAL,
                EvidenceStatus.NO_EVIDENCE,
            ),
            counts,
            strict=True,
        ):
            for index in range(count):
                needs_verification = remaining_verifications > 0
                remaining_verifications -= int(needs_verification)
                db.add(
                    EvidenceResult(
                        screening_run_id=run.id,
                        requirement_name=f"{requirement_type.value}-{result_status.value}-{index}",
                        requirement_type=requirement_type,
                        status=result_status,
                        confidence=EvidenceConfidence.HIGH,
                        explanation="Deterministic fixture evidence.",
                        needs_human_verification=needs_verification,
                    )
                )
    db.flush()
    return run


def comparison(client: TestClient, job_id: int) -> dict[str, Any]:
    response = client.get(f"/api/v1/jobs/{job_id}/candidate-comparison")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # More required support wins even against substantially more preferred support.
        ({"required": (2, 0, 0)}, {"required": (1, 1, 0), "preferred": (8, 0, 0)}),
        # With equal required support, fewer required no-evidence gaps wins.
        ({"required": (2, 0, 0)}, {"required": (2, 0, 1)}),
        # With support and gaps tied, required partial evidence is the next criterion.
        ({"required": (2, 1, 0)}, {"required": (2, 0, 0)}),
        # Preferred support breaks a required-coverage tie.
        ({"required": (2, 0, 0), "preferred": (2, 0, 0)}, {"required": (2, 0, 0), "preferred": (1, 0, 0)}),
        # Fewer unresolved items breaks the remaining evidence tie.
        ({"required": (1, 1, 0), "verification_count": 0}, {"required": (1, 1, 0), "verification_count": 1}),
    ],
    ids=[
        "required-supported-before-preferred",
        "required-no-evidence",
        "required-partial",
        "preferred-supported",
        "verification-count",
    ],
)
def test_deterministic_priority_dimensions(
    client: TestClient,
    db_session: Session,
    development_user: User,
    first: dict[str, Any],
    second: dict[str, Any],
) -> None:
    job = make_job(db_session, development_user)
    higher = make_candidate(db_session, job, "Higher")
    lower = make_candidate(db_session, job, "Lower")
    add_completed_run(db_session, higher, **first)
    add_completed_run(db_session, lower, **second)
    db_session.commit()

    result = comparison(client, job.id)

    assert [item["name"] for item in result["candidates"]] == ["Higher", "Lower"]
    assert [item["review_priority"] for item in result["candidates"]] == [1, 2]


def test_identical_coverage_uses_recent_completion_then_candidate_id(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    job = make_job(db_session, development_user)
    older = make_candidate(db_session, job, "Older")
    recent_low_id = make_candidate(db_session, job, "Recent low id")
    recent_high_id = make_candidate(db_session, job, "Recent high id")
    add_completed_run(db_session, older, required=(2, 0, 0), finished_offset=0)
    add_completed_run(db_session, recent_low_id, required=(2, 0, 0), finished_offset=2)
    add_completed_run(db_session, recent_high_id, required=(2, 0, 0), finished_offset=2)
    db_session.commit()

    result = comparison(client, job.id)

    assert [item["name"] for item in result["candidates"]] == [
        "Recent low id",
        "Recent high id",
        "Older",
    ]
    assert all(item["comparable_evidence"] for item in result["candidates"])


def test_review_labels_are_derived_only_from_visible_required_coverage(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    job = make_job(db_session, development_user)
    strong = make_candidate(db_session, job, "Strong")
    moderate = make_candidate(db_session, job, "Moderate")
    verify = make_candidate(db_session, job, "Verify")
    add_completed_run(db_session, strong, required=(3, 0, 0))
    add_completed_run(db_session, moderate, required=(1, 1, 1))
    add_completed_run(db_session, verify, required=(0, 0, 3))
    db_session.commit()

    by_name = {
        item["name"]: item
        for item in comparison(client, job.id)["candidates"]
    }

    assert by_name["Strong"]["review_label"] == "strong_evidence"
    assert by_name["Moderate"]["review_label"] == "moderate_evidence"
    assert by_name["Verify"]["review_label"] == "needs_verification"


def test_unranked_states_remain_visible_and_preserve_previous_completed_summary(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    job = make_job(db_session, development_user)
    ranked = make_candidate(db_session, job, "Ranked")
    processing = make_candidate(
        db_session, job, "Processing", status=CandidateStatus.PROCESSING
    )
    uploaded = make_candidate(
        db_session, job, "Uploaded", status=CandidateStatus.UPLOADED
    )
    failed = make_candidate(db_session, job, "Failed", status=CandidateStatus.FAILED)
    add_completed_run(db_session, ranked, required=(1, 0, 0))
    previous = add_completed_run(
        db_session, failed, required=(1, 1, 0), finished_offset=-2
    )
    db_session.add(
        ScreeningRun(
            candidate_id=processing.id,
            status=ScreeningRunStatus.PROCESSING,
            current_stage=ScreeningStage.MATCH_EVIDENCE,
            started_at=NOW,
        )
    )
    db_session.add(
        ScreeningRun(
            candidate_id=failed.id,
            status=ScreeningRunStatus.FAILED,
            current_stage=ScreeningStage.FAILED,
            started_at=NOW,
            finished_at=NOW,
            error_message="Safe failure",
        )
    )
    db_session.commit()

    result = comparison(client, job.id)
    by_name = {item["name"]: item for item in result["candidates"]}

    assert by_name["Ranked"]["review_priority"] == 1
    assert by_name["Processing"]["review_priority"] is None
    assert by_name["Processing"]["active_screening_stage"] == "match_evidence"
    assert by_name["Uploaded"]["review_priority"] is None
    assert by_name["Uploaded"]["required"] is None
    assert by_name["Failed"]["review_priority"] is None
    assert by_name["Failed"]["latest_completed_run_id"] == previous.id
    assert by_name["Failed"]["required"] == {
        "supported": 1,
        "partial": 1,
        "no_evidence": 0,
        "total": 2,
    }
    assert [item["name"] for item in result["candidates"]] == [
        "Ranked",
        "Processing",
        "Uploaded",
        "Failed",
    ]


def test_latest_completed_run_updates_priority_without_mutating_history(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    job = make_job(db_session, development_user)
    candidate = make_candidate(db_session, job, "Re-screened")
    comparison_candidate = make_candidate(db_session, job, "Comparison")
    historical = add_completed_run(
        db_session,
        candidate,
        required=(1, 0, 2),
        finished_offset=-2,
    )
    add_completed_run(
        db_session,
        comparison_candidate,
        required=(2, 0, 1),
        finished_offset=-1,
    )
    db_session.commit()
    before = comparison(client, job.id)
    assert [item["name"] for item in before["candidates"]] == [
        "Comparison",
        "Re-screened",
    ]

    replacement = add_completed_run(
        db_session,
        candidate,
        required=(3, 0, 0),
        finished_offset=1,
    )
    db_session.commit()
    after = comparison(client, job.id)

    assert [item["name"] for item in after["candidates"]] == [
        "Re-screened",
        "Comparison",
    ]
    assert after["candidates"][0]["latest_completed_run_id"] == replacement.id
    unchanged = db_session.scalar(select(ScreeningRun).where(ScreeningRun.id == historical.id))
    assert unchanged is not None
    assert unchanged.report_json == {"immutable": True, "offset": -2}
    assert unchanged.status == ScreeningRunStatus.COMPLETED


def test_response_is_job_scoped_safe_and_uses_constant_query_count(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    job = make_job(db_session, development_user)
    other_job = make_job(db_session, development_user, "Other Job")
    for index in range(12):
        candidate = make_candidate(db_session, job, f"Candidate {index}")
        add_completed_run(
            db_session,
            candidate,
            required=(index % 3, 1, 1),
            preferred=(index % 2, 0, 1),
        )
    outsider = make_candidate(db_session, other_job, "Outsider")
    add_completed_run(db_session, outsider, required=(99, 0, 0))
    db_session.commit()

    select_count = 0
    engine = db_session.get_bind()
    assert isinstance(engine, Engine)

    def count_selects(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        result = comparison(client, job.id)
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)

    serialized = str(result)
    assert result["job_id"] == job.id
    assert len(result["candidates"]) == 12
    assert "Outsider" not in serialized
    assert "PRIVATE RAW RESUME TEXT" not in serialized
    assert "resume_path" not in serialized
    assert "report_json" not in serialized
    assert "score" not in serialized.lower()
    assert select_count == 2


def test_other_users_job_is_not_accessible(
    client: TestClient,
    db_session: Session,
) -> None:
    other_user = User(
        email="other@example.com",
        password_hash="not-authenticated",
        full_name="Other Recruiter",
    )
    db_session.add(other_user)
    db_session.flush()
    other_job = make_job(db_session, other_user)
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{other_job.id}/candidate-comparison")

    assert response.status_code == 404
