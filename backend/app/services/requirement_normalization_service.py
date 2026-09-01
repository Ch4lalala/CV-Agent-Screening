"""Deterministic authority controls for AI-normalized requirements."""

import re

from app.agents.schemas import (
    JobRequirementAI,
    JobRequirementsResponse,
    RecruiterRequirement,
)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _safe_normalized_name(original: str, proposed: str) -> str:
    original_folded = original.casefold()
    proposed_folded = proposed.casefold()
    if original_folded in proposed_folded or proposed_folded in original_folded:
        return proposed
    if _tokens(original) & _tokens(proposed):
        return proposed
    return original


def reconcile_requirements(
    existing: list[RecruiterRequirement],
    ai_response: JobRequirementsResponse,
) -> list[JobRequirementAI]:
    """Preserve recruiter authority and accept AI derivation only when needed."""

    if existing:
        ai_by_id = {
            item.source_requirement_id: item
            for item in ai_response.requirements
            if item.source_requirement_id is not None
        }
        normalized: list[JobRequirementAI] = []
        for manual in existing:
            suggestion = ai_by_id.get(manual.id)
            normalized.append(
                JobRequirementAI(
                    source_requirement_id=manual.id,
                    name=(
                        _safe_normalized_name(manual.name, suggestion.name)
                        if suggestion is not None
                        else manual.name
                    ),
                    description=(
                        suggestion.description
                        if suggestion is not None and suggestion.description
                        else manual.description
                    ),
                    requirement_type=manual.requirement_type,
                    source="recruiter",
                    priority=manual.priority,
                    recruiter_name=manual.name,
                    recruiter_description=manual.description,
                )
            )
        return normalized

    normalized = []
    seen_names: set[str] = set()
    for item in ai_response.requirements:
        name_key = " ".join(item.name.casefold().split())
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        normalized.append(
            JobRequirementAI(
                source_requirement_id=None,
                name=item.name,
                description=item.description,
                requirement_type=item.requirement_type,
                source="ai_derived",
                priority=item.priority,
            )
        )
    return normalized
