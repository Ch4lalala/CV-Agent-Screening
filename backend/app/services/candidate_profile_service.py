"""Deterministic checks for candidate-profile fields requiring exact grounding."""

from app.agents.schemas import CandidateProfile
from app.services.evidence_service import quote_exists_in_resume


def retain_candidate_provided_urls(
    profile: CandidateProfile,
    resume_text: str,
) -> CandidateProfile:
    """Discard URLs that do not occur in the candidate-provided resume text."""

    return profile.model_copy(
        update={
            "github_urls": [
                url
                for url in profile.github_urls
                if quote_exists_in_resume(url, resume_text)
            ],
            "portfolio_urls": [
                url
                for url in profile.portfolio_urls
                if quote_exists_in_resume(url, resume_text)
            ],
        }
    )
