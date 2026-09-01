from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import BaseMessage
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.client import get_ai_client
from app.ai.exceptions import AIProviderError
from app.main import app
from app.models import Job, JobRequirement
from app.schemas.job_import import JobImportDraft


MANUAL_DESCRIPTION = """Minimum Qualifications:
- Currently pursuing an undergraduate degree in a related technical discipline.
- Expertise with Golang or a similar programming language.
- Strong understanding of SQL or relational databases.
- Understanding of high-volume distributed backend services.

Preferred Qualifications:
- Experience with React.js or a modern JavaScript framework.
- Experience building scalable websites or large-scale applications.
- Strong debugging skills.
"""


class ManualDraftAIClient:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[Sequence[BaseMessage]] = []

    async def invoke_structured(
        self,
        _: object,
        messages: Sequence[BaseMessage],
    ) -> JobImportDraft:
        self.calls.append(messages)
        result = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        if isinstance(result, Exception):
            raise result
        return JobImportDraft.model_validate(result)


def install_ai(client: ManualDraftAIClient) -> ManualDraftAIClient:
    app.dependency_overrides[get_ai_client] = lambda: client
    return client


def seven_requirement_draft() -> dict[str, object]:
    return {
        "title": "AI title must not replace recruiter title",
        "description": "AI description must not replace recruiter description.",
        "requirements": [
            {
                "name": "Relevant undergraduate technical education",
                "description": "Currently pursuing an undergraduate degree in a related technical discipline.",
                "type": "required",
            },
            {
                "name": "Backend programming language proficiency",
                "description": "Experience with Go or a comparable programming language.",
                "type": "required",
            },
            {
                "name": "SQL / relational database knowledge",
                "description": "Understanding of SQL or relational databases.",
                "type": "required",
            },
            {
                "name": "Distributed backend systems experience",
                "description": "Understanding of high-volume distributed backend services.",
                "type": "required",
            },
            {
                "name": "Modern JavaScript framework experience",
                "description": "Experience with React.js or another modern JavaScript framework.",
                "type": "preferred",
            },
            {
                "name": "Scalable web application experience",
                "description": "Experience building scalable websites or large-scale applications.",
                "type": "preferred",
            },
            {
                "name": "Debugging skills",
                "description": "Demonstrated software debugging skills.",
                "type": "preferred",
            },
        ],
        "warnings": [],
    }


def test_manual_description_generates_required_and_preferred_draft_without_persistence(
    client: TestClient,
    db_session: Session,
) -> None:
    ai_client = install_ai(ManualDraftAIClient(seven_requirement_draft()))

    response = client.post(
        "/api/v1/jobs/analyze-description",
        json={"title": "Backend Engineer Intern", "description": MANUAL_DESCRIPTION},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Backend Engineer Intern"
    assert body["description"] == MANUAL_DESCRIPTION.strip()
    assert [item["type"] for item in body["requirements"]] == [
        "required",
        "required",
        "required",
        "required",
        "preferred",
        "preferred",
        "preferred",
    ]
    assert body["requirements"][1] == {
        "name": "Backend programming language proficiency",
        "description": "Experience with Go or a comparable programming language.",
        "type": "required",
    }
    assert db_session.scalar(select(func.count()).select_from(Job)) == 0
    assert db_session.scalar(select(func.count()).select_from(JobRequirement)) == 0

    source_text = str(ai_client.calls[0][1].content)
    assert "Backend Engineer Intern" in source_text
    assert MANUAL_DESCRIPTION.strip() in source_text


def test_manual_analysis_prompt_covers_heading_and_sentence_signals(
    client: TestClient,
) -> None:
    ai_client = install_ai(ManualDraftAIClient(seven_requirement_draft()))

    response = client.post(
        "/api/v1/jobs/analyze-description",
        json={
            "title": "Engineer",
            "description": (
                "Minimum Qualifications: Git is required. Candidates must have SQL. "
                "Preferred Qualifications: Docker experience is a plus. AWS is preferred."
            ),
        },
    )

    assert response.status_code == 200
    system_text = str(ai_client.calls[0][0].content)
    for signal in (
        "Minimum Qualifications",
        "Must Have",
        "Preferred Qualifications",
        "Nice to Have",
        "is a plus",
        "is preferred",
        "is required",
    ):
        assert signal in system_text


def test_manual_known_composites_are_split_into_atomic_requirements(
    client: TestClient,
) -> None:
    composite = {
        "title": "Engineer",
        "description": "Role description",
        "requirements": [
            {"name": "Go, REST API, PostgreSQL, and Git", "type": "required"},
            {"name": "Docker, CI/CD, and AWS", "type": "preferred"},
        ],
        "warnings": [],
    }
    ai_client = install_ai(ManualDraftAIClient(composite, composite))

    response = client.post(
        "/api/v1/jobs/analyze-description",
        json={
            "title": "Engineer",
            "description": "Required: Go, REST API, PostgreSQL, Git. Preferred: Docker, CI/CD, AWS.",
        },
    )

    assert response.status_code == 200
    assert len(ai_client.calls) == 2
    assert [item["name"] for item in response.json()["requirements"]] == [
        "Go",
        "REST API Development",
        "PostgreSQL",
        "Git",
        "Docker",
        "CI/CD",
        "AWS",
    ]


def test_manual_ai_failure_is_sanitized_and_does_not_persist(
    client: TestClient,
    db_session: Session,
) -> None:
    install_ai(ManualDraftAIClient(AIProviderError("provider leaked-secret")))

    response = client.post(
        "/api/v1/jobs/analyze-description",
        json={"title": "Engineer", "description": "Candidates must have Git."},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "AI service is temporarily unavailable."}
    assert "leaked-secret" not in response.text
    assert db_session.scalar(select(func.count()).select_from(Job)) == 0


def test_recruiter_confirmation_persists_edited_atomic_rows(
    client: TestClient,
    db_session: Session,
) -> None:
    install_ai(ManualDraftAIClient(seven_requirement_draft()))
    analysis = client.post(
        "/api/v1/jobs/analyze-description",
        json={"title": "Backend Engineer Intern", "description": MANUAL_DESCRIPTION},
    ).json()

    requirements = analysis["requirements"]
    requirements[0]["name"] = "Edited technical education"
    requirements[4]["type"] = "required"
    requirements.pop()
    requirements.append(
        {
            "name": "Observability fundamentals",
            "description": "Experience diagnosing services with logs and metrics.",
            "type": "preferred",
        }
    )

    job_response = client.post(
        "/api/v1/jobs",
        json={"title": analysis["title"], "description": analysis["description"]},
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]
    for priority, requirement in enumerate(requirements, start=1):
        response = client.post(
            f"/api/v1/jobs/{job_id}/requirements",
            json={
                "name": requirement["name"],
                "description": requirement.get("description"),
                "requirement_type": requirement["type"],
                "priority": priority,
            },
        )
        assert response.status_code == 201

    persisted = client.get(f"/api/v1/jobs/{job_id}/requirements").json()
    assert len(persisted) == 7
    assert len({item["id"] for item in persisted}) == 7
    assert persisted[0]["name"] == "Edited technical education"
    assert persisted[4]["requirement_type"] == "required"
    assert persisted[-1]["name"] == "Observability fundamentals"
    assert db_session.scalar(select(func.count()).select_from(JobRequirement)) == 7


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "", "description": "Valid description"},
        {"title": "Engineer", "description": ""},
        {"title": "Engineer", "description": "Valid", "unexpected": True},
    ],
)
def test_manual_analysis_input_is_strict(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    install_ai(ManualDraftAIClient(seven_requirement_draft()))
    assert client.post("/api/v1/jobs/analyze-description", json=payload).status_code == 422
