import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.graph import get_recruitment_graph
from app.agents.schemas import CandidateProfile, CoverageSummary, ScreeningReport
from app.ai.client import get_ai_client, get_chat_model
from app.ai.config import get_ai_settings
from app.ai.exceptions import AIProviderError
from app.models import Candidate, Job, ResumeDocument, ScreeningRun, User
from app.models.enums import CandidateStatus, ResumeExtractionStatus, ScreeningRunStatus
from app.schemas.screening import CandidateReportResponse
from app.services import screening_service


class FakeGraph:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    async def ainvoke(self, _: object) -> object:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def create_candidate_with_resume(
    db: Session,
    user: User,
    *,
    resume_status: ResumeExtractionStatus | None,
    extracted_text: str | None = "Skills: Go",
) -> Candidate:
    job = Job(
        user_id=user.id,
        title="Backend Engineer",
        description="Build backend services.",
    )
    db.add(job)
    db.flush()
    candidate = Candidate(
        job_id=job.id,
        name="Synthetic Candidate",
        status=CandidateStatus.UPLOADED,
    )
    db.add(candidate)
    db.flush()
    if resume_status is not None:
        db.add(
            ResumeDocument(
                candidate_id=candidate.id,
                extracted_text=extracted_text,
                page_count=1,
                extraction_status=resume_status,
            )
        )
    db.commit()
    db.refresh(candidate)
    return candidate


def empty_report(candidate: Candidate) -> ScreeningReport:
    return ScreeningReport(
        job_id=str(candidate.job_id),
        candidate_id=str(candidate.id),
        job_title="Backend Engineer",
        normalized_requirements=[],
        candidate_profile=CandidateProfile(skills=["Go"]),
        required_coverage=CoverageSummary(supported=0, total=0),
        preferred_coverage=CoverageSummary(supported=0, total=0),
        evidence_results=[],
        needs_verification=[],
        interview_questions=[],
        security_warning=None,
    )


def test_screening_missing_candidate_returns_404(client: TestClient) -> None:
    response = client.post("/api/v1/candidates/999999/screen")

    assert response.status_code == 404
    assert response.json() == {"detail": "Candidate not found"}


def test_screening_missing_resume_returns_404(
    client: TestClient,
    db_session: Session,
    development_user: User,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=None,
    )

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resume not found"}


@pytest.mark.parametrize(
    "resume_status, extracted_text",
    [
        (ResumeExtractionStatus.PENDING, None),
        (ResumeExtractionStatus.FAILED, None),
        (ResumeExtractionStatus.COMPLETED, ""),
    ],
)
def test_screening_incomplete_extraction_returns_409(
    client: TestClient,
    db_session: Session,
    development_user: User,
    resume_status: ResumeExtractionStatus,
    extracted_text: str | None,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=resume_status,
        extracted_text=extracted_text,
    )

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 409
    assert response.json() == {"detail": "Resume extraction is not completed"}


def test_screening_missing_ai_configuration_is_sanitized(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=ResumeExtractionStatus.COMPLETED,
    )
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    get_ai_settings.cache_clear()
    get_chat_model.cache_clear()
    get_ai_client.cache_clear()
    get_recruitment_graph.cache_clear()

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service is not configured"}
    assert "AI_API_KEY" not in response.text
    get_ai_settings.cache_clear()
    get_chat_model.cache_clear()
    get_ai_client.cache_clear()
    get_recruitment_graph.cache_clear()


def test_screening_provider_failure_is_sanitized(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=ResumeExtractionStatus.COMPLETED,
    )
    graph = FakeGraph(AIProviderError("provider returned private-secret"))
    monkeypatch.setattr(screening_service, "get_recruitment_graph", lambda: graph)

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 503
    assert response.json() == {"detail": "AI screening is temporarily unavailable"}
    assert "private-secret" not in response.text


def test_screening_returns_persisted_report_and_changes_status(
    client: TestClient,
    db_session: Session,
    development_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=ResumeExtractionStatus.COMPLETED,
    )
    graph = FakeGraph({"final_report": empty_report(candidate)})
    monkeypatch.setattr(screening_service, "get_recruitment_graph", lambda: graph)

    response = client.post(f"/api/v1/candidates/{candidate.id}/screen")

    assert response.status_code == 200
    assert response.json()["candidate"]["id"] == candidate.id
    assert response.json()["screening_run"]["status"] == "completed"
    assert "decision" not in response.json()
    db_session.refresh(candidate)
    assert candidate.status == CandidateStatus.COMPLETED
    run = db_session.query(ScreeningRun).one()
    assert run.status == ScreeningRunStatus.COMPLETED
    assert run.report_json is not None
    assert graph.calls == 1


def test_screening_service_accepts_an_injected_graph(
    db_session: Session,
    development_user: User,
) -> None:
    candidate = create_candidate_with_resume(
        db_session,
        development_user,
        resume_status=ResumeExtractionStatus.COMPLETED,
    )
    graph = FakeGraph({"final_report": empty_report(candidate)})

    report = asyncio.run(
        screening_service.screen_candidate(
            db_session,
            candidate_id=candidate.id,
            user_id=development_user.id,
            graph=graph,
        )
    )

    assert isinstance(report, CandidateReportResponse)
    assert report.candidate.id == candidate.id
