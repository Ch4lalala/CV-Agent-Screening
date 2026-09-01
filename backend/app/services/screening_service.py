"""Load database inputs, run LangGraph, and return a non-persistent report."""

import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.graph import get_recruitment_graph
from app.agents.schemas import RecruiterRequirement, ScreeningReport
from app.agents.state import RecruitmentState
from app.ai.exceptions import AIConfigurationError, AIProviderError, AIStructuredOutputError
from app.models.enums import ResumeExtractionStatus
from app.repositories import candidates, job_requirements, jobs, resume_documents

logger = logging.getLogger(__name__)


class ScreeningInputNotFoundError(Exception):
    pass


class ResumeNotReadyError(Exception):
    pass


class ScreeningExecutionError(Exception):
    pass


async def screen_candidate(
    db: Session,
    *,
    candidate_id: int,
    user_id: int,
    graph: object | None = None,
) -> ScreeningReport:
    """Run screening without storing output or changing candidate status."""

    candidate = candidates.get_for_user(
        db,
        candidate_id=candidate_id,
        user_id=user_id,
    )
    if candidate is None:
        raise ScreeningInputNotFoundError("Candidate not found")

    job = jobs.get_for_user(db, job_id=candidate.job_id, user_id=user_id)
    if job is None:
        raise ScreeningInputNotFoundError("Job not found")

    resume = resume_documents.get_for_candidate(db, candidate_id=candidate.id)
    if resume is None:
        raise ScreeningInputNotFoundError("Resume not found")
    if (
        resume.extraction_status != ResumeExtractionStatus.COMPLETED
        or not resume.extracted_text
    ):
        raise ResumeNotReadyError("Resume extraction is not completed")

    requirements = job_requirements.list_for_job(db, job_id=job.id)
    initial_state: RecruitmentState = {
        "job_id": str(job.id),
        "candidate_id": str(candidate.id),
        "job_title": job.title,
        "job_description": job.description,
        "existing_requirements": [
            RecruiterRequirement(
                id=item.id,
                name=item.name,
                description=item.description,
                requirement_type=item.requirement_type.value,
                priority=item.priority,
            )
            for item in requirements
        ],
        "resume_text": resume.extracted_text,
        "errors": [],
    }

    logger.info(
        "Candidate screening started",
        extra={"candidate_id": candidate.id, "job_id": job.id},
    )
    screening_graph = graph or get_recruitment_graph()
    try:
        result = await screening_graph.ainvoke(initial_state)  # type: ignore[attr-defined]
        report = ScreeningReport.model_validate(result["final_report"])
    except (AIConfigurationError, AIProviderError, AIStructuredOutputError):
        logger.warning(
            "Candidate screening AI request failed",
            extra={"candidate_id": candidate.id, "job_id": job.id},
        )
        raise
    except (KeyError, TypeError, ValidationError) as exc:
        logger.error(
            "Candidate screening returned an invalid result",
            extra={"candidate_id": candidate.id, "job_id": job.id},
        )
        raise ScreeningExecutionError("Candidate screening failed") from exc
    except Exception as exc:
        logger.error(
            "Candidate screening failed (%s)",
            type(exc).__name__,
            extra={"candidate_id": candidate.id, "job_id": job.id},
        )
        raise ScreeningExecutionError("Candidate screening failed") from exc

    logger.info(
        "Candidate screening completed",
        extra={"candidate_id": candidate.id, "job_id": job.id},
    )
    return report
