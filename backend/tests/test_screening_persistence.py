import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.schemas import (
    CandidateProfile as CandidateProfileSchema,
    CoverageSummary,
    EvidenceAssessment,
    EvidenceItem as EvidenceItemSchema,
    InterviewQuestion as InterviewQuestionSchema,
    JobRequirementAI,
    ScreeningReport,
)
from app.ai.exceptions import AIProviderError
from app.models import (
    Candidate,
    CandidateProfile,
    EvidenceItem,
    EvidenceResult,
    InterviewQuestion,
    Job,
    JobRequirement,
    ResumeDocument,
    ScreeningRun,
    User,
)
from app.models.enums import (
    CandidateStatus,
    RequirementType,
    ResumeExtractionStatus,
    ScreeningRunStatus,
)
from app.services import screening_service


class FakeGraph:
    def __init__(
        self,
        results: list[object],
        on_invoke: Callable[[], None] | None = None,
    ) -> None:
        self.results = results
        self.on_invoke = on_invoke
        self.calls = 0

    async def ainvoke(self, _: object) -> object:
        if self.on_invoke is not None:
            self.on_invoke()
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


def candidate_with_requirement(
    db: Session,
    user: User,
    *,
    resume_path: str | None = None,
) -> tuple[Candidate, JobRequirement]:
    job = Job(
        user_id=user.id,
        title="Backend Engineer",
        description="Build reliable Go services.",
    )
    db.add(job)
    db.flush()
    requirement = JobRequirement(
        job_id=job.id,
        name="Go",
        description="Production Go experience",
        requirement_type=RequirementType.REQUIRED,
        priority=1,
    )
    candidate = Candidate(
        job_id=job.id,
        name="Synthetic Candidate",
        email="candidate@example.com",
        original_filename="candidate.pdf" if resume_path else None,
        resume_path=resume_path,
        status=CandidateStatus.UPLOADED,
    )
    db.add_all([requirement, candidate])
    db.flush()
    db.add(
        ResumeDocument(
            candidate_id=candidate.id,
            extracted_text="Skills\nGo and PostgreSQL",
            page_count=1,
            extraction_status=ResumeExtractionStatus.COMPLETED,
        )
    )
    db.commit()
    return candidate, requirement


def report_for(
    candidate: Candidate,
    *,
    requirement_id: int | None,
    skill: str = "Go",
    supported: bool = True,
    ai_derived: bool = False,
) -> ScreeningReport:
    source = "ai_derived" if ai_derived else "recruiter"
    status = "supported" if supported else "partial"
    return ScreeningReport(
        job_id=str(candidate.job_id),
        candidate_id=str(candidate.id),
        job_title="Backend Engineer",
        normalized_requirements=[
            JobRequirementAI(
                source_requirement_id=requirement_id,
                name=skill,
                description=f"{skill} experience",
                requirement_type="required",
                source=source,
                priority=1,
                recruiter_name=None if ai_derived else "Go",
                recruiter_description=(
                    None if ai_derived else "Production Go experience"
                ),
            )
        ],
        candidate_profile=CandidateProfileSchema(
            candidate_name="Synthetic Candidate",
            email="candidate@example.com",
            skills=[skill],
        ),
        required_coverage=CoverageSummary(
            supported=1 if supported else 0,
            total=1,
        ),
        preferred_coverage=CoverageSummary(supported=0, total=0),
        evidence_results=[
            EvidenceAssessment(
                requirement_index=0,
                source_requirement_id=requirement_id,
                requirement=skill,
                requirement_type="required",
                requirement_source=source,
                status=status,
                confidence="high" if supported else "medium",
                explanation=f"Resume evidence for {skill}.",
                needs_human_verification=not supported,
                evidence=[
                    EvidenceItemSchema(
                        quote="Go and PostgreSQL",
                        source_section="Skills",
                        source_page=1,
                    )
                ],
            )
        ],
        needs_verification=[] if supported else [skill],
        interview_questions=[
            InterviewQuestionSchema(
                requirement=skill,
                requirement_type="required",
                question=f"Can you describe your production work with {skill}?",
                reason=f"Validate the candidate's {skill} experience.",
            )
        ],
        security_warning=None,
    )


def install_graph(
    monkeypatch: pytest.MonkeyPatch,
    *results: object,
    on_invoke: Callable[[], None] | None = None,
) -> FakeGraph:
    graph = FakeGraph(list(results), on_invoke=on_invoke)
    monkeypatch.setattr(screening_service, "get_recruitment_graph", lambda: graph)
    return graph


def test_successful_run_persists_full_report_and_model_name(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, requirement = candidate_with_requirement(db_session, development_user)
    report = report_for(candidate, requirement_id=requirement.id)
    monkeypatch.setenv("AI_MODEL", "test-model-v1")
    install_graph(monkeypatch, {"final_report": report})

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 200
    payload = response.json()
    run = db_session.scalar(select(ScreeningRun))
    assert run is not None
    assert run.status == ScreeningRunStatus.COMPLETED
    assert run.started_at is not None
    assert run.finished_at is not None
    assert run.model_name == "test-model-v1"
    assert run.report_json == report.model_dump(mode="json")
    assert payload["screening_run"]["id"] == run.id
    assert payload["screening_run"]["model_name"] == "test-model-v1"
    assert payload["coverage"]["required"] == {"supported": 1, "total": 1}

    profile = db_session.scalar(select(CandidateProfile))
    evidence_result = db_session.scalar(select(EvidenceResult))
    evidence_item = db_session.scalar(select(EvidenceItem))
    question = db_session.scalar(select(InterviewQuestion))
    assert profile is not None
    assert profile.profile_json["skills"] == ["Go"]
    assert evidence_result is not None
    assert evidence_result.requirement_id == requirement.id
    assert evidence_result.requirement_name == "Go"
    assert evidence_item is not None
    assert evidence_item.quote == "Go and PostgreSQL"
    assert question is not None
    assert "production work" in question.question


def test_run_and_candidate_are_processing_during_graph_then_completed(
    db_session: Session,
    development_user: User,
) -> None:
    candidate, requirement = candidate_with_requirement(db_session, development_user)
    observed: dict[str, object] = {}

    def inspect_committed_start_state() -> None:
        observed["transaction_open"] = db_session.in_transaction()
        db_session.expire_all()
        current_candidate = db_session.get(Candidate, candidate.id)
        current_run = db_session.scalar(select(ScreeningRun))
        observed["candidate_status"] = current_candidate.status
        observed["run_status"] = current_run.status

    graph = FakeGraph(
        [{"final_report": report_for(candidate, requirement_id=requirement.id)}],
        on_invoke=inspect_committed_start_state,
    )

    response = asyncio.run(
        screening_service.screen_candidate(
            db_session,
            candidate_id=candidate.id,
            user_id=development_user.id,
            graph=graph,
        )
    )

    assert observed == {
        "transaction_open": False,
        "candidate_status": CandidateStatus.PROCESSING,
        "run_status": ScreeningRunStatus.PROCESSING,
    }
    db_session.refresh(candidate)
    assert response.screening_run.status == ScreeningRunStatus.COMPLETED
    assert candidate.status == CandidateStatus.COMPLETED


def test_latest_history_and_specific_report_endpoints(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, requirement = candidate_with_requirement(db_session, development_user)
    report = report_for(candidate, requirement_id=requirement.id)
    install_graph(monkeypatch, {"final_report": report})
    created = client.post(f"/api/v1/candidates/{candidate.id}/screen").json()
    run_id = created["screening_run"]["id"]

    latest = client.get(f"/api/v1/candidates/{candidate.id}/screening")
    history = client.get(f"/api/v1/candidates/{candidate.id}/screenings")
    specific = client.get(f"/api/v1/candidates/{candidate.id}/screenings/{run_id}")

    assert latest.status_code == 200
    assert latest.json() == created
    assert history.status_code == 200
    assert [item["id"] for item in history.json()] == [run_id]
    assert "report_json" not in history.text
    assert "candidate_profile" not in history.text
    assert specific.status_code == 200
    assert specific.json() == created


def test_second_run_creates_new_immutable_historical_snapshot(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, requirement = candidate_with_requirement(db_session, development_user)
    first_report = report_for(candidate, requirement_id=requirement.id, skill="Go")
    second_report = report_for(
        candidate,
        requirement_id=requirement.id,
        skill="PostgreSQL",
        supported=False,
    )
    install_graph(
        monkeypatch,
        {"final_report": first_report},
        {"final_report": second_report},
    )

    first = client.post(f"/api/v1/candidates/{candidate.id}/screen").json()
    second = client.post(f"/api/v1/candidates/{candidate.id}/screen").json()

    assert first["screening_run"]["id"] != second["screening_run"]["id"]
    history = client.get(f"/api/v1/candidates/{candidate.id}/screenings").json()
    assert [item["id"] for item in history] == [
        second["screening_run"]["id"],
        first["screening_run"]["id"],
    ]
    latest = client.get(f"/api/v1/candidates/{candidate.id}/screening").json()
    historical = client.get(
        f"/api/v1/candidates/{candidate.id}/screenings/"
        f"{first['screening_run']['id']}"
    ).json()
    assert latest["candidate_profile"]["skills"] == ["PostgreSQL"]
    assert historical["candidate_profile"]["skills"] == ["Go"]
    assert historical["evidence_results"][0]["requirement_name"] == "Go"


@pytest.mark.parametrize("active_record", ["candidate", "run"])
def test_concurrent_processing_returns_409(
    client: TestClient,
    db_session: Session,
    development_user: User,
    active_record: str,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)
    if active_record == "candidate":
        candidate.status = CandidateStatus.PROCESSING
    else:
        db_session.add(
            ScreeningRun(
                candidate_id=candidate.id,
                status=ScreeningRunStatus.PROCESSING,
            )
        )
    db_session.commit()

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 409
    assert response.json() == {"detail": "Candidate screening is already in progress."}


def test_ai_failure_persists_safe_failure_and_candidate_status(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)
    monkeypatch.setenv("AI_MODEL", "safe-model")
    install_graph(monkeypatch, AIProviderError("secret-provider-detail"))

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 503
    assert "secret-provider-detail" not in response.text
    db_session.expire_all()
    run = db_session.scalar(select(ScreeningRun))
    current_candidate = db_session.get(Candidate, candidate.id)
    assert run is not None
    assert run.status == ScreeningRunStatus.FAILED
    assert run.finished_at is not None
    assert run.error_message == "AI provider is temporarily unavailable."
    assert "secret-provider-detail" not in run.error_message
    assert run.model_name == "safe-model"
    assert current_candidate.status == CandidateStatus.FAILED


def test_ai_derived_requirement_persists_null_requirement_id(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)
    report = report_for(
        candidate,
        requirement_id=None,
        skill="Distributed systems",
        ai_derived=True,
    )
    install_graph(monkeypatch, {"final_report": report})

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 200
    evidence = db_session.scalar(select(EvidenceResult))
    assert evidence is not None
    assert evidence.requirement_id is None
    assert evidence.requirement_name == "Distributed systems"


def test_untrusted_recruiter_requirement_id_is_not_mapped(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)
    other_job = Job(
        user_id=development_user.id,
        title="Other role",
        description="Other description",
    )
    db_session.add(other_job)
    db_session.flush()
    other_requirement = JobRequirement(
        job_id=other_job.id,
        name="Go",
        requirement_type=RequirementType.REQUIRED,
    )
    db_session.add(other_requirement)
    db_session.commit()
    report = report_for(candidate, requirement_id=other_requirement.id)
    install_graph(monkeypatch, {"final_report": report})

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 200
    evidence = db_session.scalar(select(EvidenceResult))
    assert evidence.requirement_id is None


def test_cross_candidate_run_access_returns_404(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_candidate, requirement = candidate_with_requirement(
        db_session, development_user
    )
    second_candidate, _ = candidate_with_requirement(db_session, development_user)
    install_graph(
        monkeypatch,
        {"final_report": report_for(first_candidate, requirement_id=requirement.id)},
    )
    run_id = client.post(f"/api/v1/candidates/{first_candidate.id}/screen").json()[
        "screening_run"
    ]["id"]

    response = client.get(
        f"/api/v1/candidates/{second_candidate.id}/screenings/{run_id}"
    )

    assert response.status_code == 404


def test_no_completed_report_returns_404(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)

    response = client.get(f"/api/v1/candidates/{candidate.id}/screening")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "No completed screening report exists for this candidate."
    }


def test_failed_run_is_in_history_but_not_available_as_report(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, _ = candidate_with_requirement(db_session, development_user)
    install_graph(monkeypatch, AIProviderError("private"))
    client.post(f"/api/v1/candidates/{candidate.id}/screen")
    run = db_session.scalar(select(ScreeningRun))

    history = client.get(f"/api/v1/candidates/{candidate.id}/screenings")
    latest = client.get(f"/api/v1/candidates/{candidate.id}/screening")
    specific = client.get(f"/api/v1/candidates/{candidate.id}/screenings/{run.id}")

    assert history.status_code == 200
    assert history.json()[0]["status"] == "failed"
    assert history.json()[0]["error_message"] == (
        "AI provider is temporarily unavailable."
    )
    assert latest.status_code == 404
    assert specific.status_code == 404


def test_candidate_delete_cascades_screening_rows_and_removes_resume_file(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
    resume_storage_path: Path,
) -> None:
    stored_filename = "persisted-candidate.pdf"
    stored_path = resume_storage_path / stored_filename
    stored_path.parent.mkdir(parents=True)
    stored_path.write_bytes(b"%PDF-test")
    candidate, requirement = candidate_with_requirement(
        db_session,
        development_user,
        resume_path=stored_filename,
    )
    install_graph(
        monkeypatch,
        {"final_report": report_for(candidate, requirement_id=requirement.id)},
    )
    client.post(f"/api/v1/candidates/{candidate.id}/screen")

    response = client.delete(f"/api/v1/candidates/{candidate.id}")

    assert response.status_code == 204
    assert not stored_path.exists()
    assert db_session.scalar(select(ScreeningRun)) is None
    assert db_session.scalar(select(CandidateProfile)) is None
    assert db_session.scalar(select(EvidenceResult)) is None
    assert db_session.scalar(select(EvidenceItem)) is None
    assert db_session.scalar(select(InterviewQuestion)) is None


def test_report_response_does_not_expose_resume_or_provider_secrets(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate, requirement = candidate_with_requirement(db_session, development_user)
    monkeypatch.setenv("AI_API_KEY", "never-return-this-key")
    monkeypatch.setenv("AI_BASE_URL", "https://private-provider.invalid")
    install_graph(
        monkeypatch,
        {"final_report": report_for(candidate, requirement_id=requirement.id)},
    )

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 200
    serialized = response.text
    assert "never-return-this-key" not in serialized
    assert "private-provider" not in serialized
    assert "resume_path" not in serialized
    assert "extracted_text" not in serialized
    assert "raw_prompt" not in serialized
