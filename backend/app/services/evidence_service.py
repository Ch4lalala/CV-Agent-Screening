"""Conservative evidence verification and deterministic uncertainty grouping."""

import re
import unicodedata

from app.agents.schemas import (
    EvidenceAnalysisResponse,
    EvidenceAssessment,
    EvidenceAssessmentDraft,
    EvidenceItem,
    JobRequirementAI,
)


def normalize_evidence_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u00ad", "").replace("\u200b", "")
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def quote_exists_in_resume(quote: str, resume_text: str) -> bool:
    normalized_quote = normalize_evidence_text(quote)
    normalized_resume = normalize_evidence_text(resume_text)
    if not normalized_quote or not normalized_resume:
        return False

    pattern = re.escape(normalized_quote)
    if normalized_quote[0].isalnum():
        pattern = rf"(?<!\w){pattern}"
    if normalized_quote[-1].isalnum():
        pattern = rf"{pattern}(?!\w)"
    return re.search(pattern, normalized_resume) is not None


def _no_evidence_assessment(
    index: int,
    requirement: JobRequirementAI,
    *,
    needs_human_verification: bool,
) -> EvidenceAssessment:
    return EvidenceAssessment(
        requirement_index=index,
        source_requirement_id=requirement.source_requirement_id,
        requirement=requirement.name,
        requirement_type=requirement.requirement_type,
        requirement_source=requirement.source,
        status="no_evidence",
        confidence="low",
        explanation=(
            f"No evidence of {requirement.name} was found in the provided resume."
        ),
        needs_human_verification=needs_human_verification,
        evidence=[],
    )


def _validated_assessment(
    index: int,
    requirement: JobRequirementAI,
    draft: EvidenceAssessmentDraft,
    resume_text: str,
) -> EvidenceAssessment:
    if draft.status == "no_evidence":
        return _no_evidence_assessment(
            index,
            requirement,
            needs_human_verification=requirement.requirement_type == "required",
        )

    verified: list[EvidenceItem] = []
    rejected_quote = False
    for item in draft.evidence:
        if quote_exists_in_resume(item.quote, resume_text):
            verified.append(
                EvidenceItem(
                    quote=item.quote,
                    source_section=item.source_section,
                    source_page=None,
                )
            )
        else:
            rejected_quote = True

    if not verified:
        return _no_evidence_assessment(
            index,
            requirement,
            needs_human_verification=True,
        )

    status = draft.status
    confidence = draft.confidence
    if status == "partial" and confidence == "high":
        confidence = "medium"
    if rejected_quote and confidence == "high":
        confidence = "medium"

    needs_verification = (
        status == "partial"
        or confidence != "high"
        or rejected_quote
        or draft.needs_human_verification
    )
    if status == "supported" and confidence == "high" and not rejected_quote:
        needs_verification = False

    return EvidenceAssessment(
        requirement_index=index,
        source_requirement_id=requirement.source_requirement_id,
        requirement=requirement.name,
        requirement_type=requirement.requirement_type,
        requirement_source=requirement.source,
        status=status,
        confidence=confidence,
        explanation=draft.explanation,
        needs_human_verification=needs_verification,
        evidence=verified,
    )


def validate_evidence_assessments(
    requirements: list[JobRequirementAI],
    ai_response: EvidenceAnalysisResponse,
    resume_text: str,
) -> list[EvidenceAssessment]:
    """Return one grounded assessment for every normalized requirement."""

    drafts_by_index: dict[int, EvidenceAssessmentDraft] = {}
    for draft in ai_response.assessments:
        if draft.requirement_index < len(requirements):
            drafts_by_index.setdefault(draft.requirement_index, draft)

    results: list[EvidenceAssessment] = []
    for index, requirement in enumerate(requirements):
        draft = drafts_by_index.get(index)
        if draft is None:
            results.append(
                _no_evidence_assessment(
                    index,
                    requirement,
                    needs_human_verification=(
                        requirement.requirement_type == "required"
                    ),
                )
            )
            continue
        results.append(_validated_assessment(index, requirement, draft, resume_text))
    return results


def group_requirements_by_evidence(
    requirements: list[JobRequirementAI],
    assessments: list[EvidenceAssessment],
) -> dict[str, list[JobRequirementAI]]:
    requirement_by_index = {index: item for index, item in enumerate(requirements)}
    grouped: dict[str, list[JobRequirementAI]] = {
        "supported_requirements": [],
        "partial_requirements": [],
        "missing_requirements": [],
    }
    keys = {
        "supported": "supported_requirements",
        "partial": "partial_requirements",
        "no_evidence": "missing_requirements",
    }
    for assessment in assessments:
        requirement = requirement_by_index.get(assessment.requirement_index)
        if requirement is not None:
            grouped[keys[assessment.status]].append(requirement)
    return grouped
