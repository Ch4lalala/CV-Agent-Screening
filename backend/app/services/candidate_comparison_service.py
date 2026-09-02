"""Transparent, deterministic vacancy-level candidate prioritization."""

from collections import Counter
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import CandidateStatus
from app.repositories import candidate_comparison
from app.schemas.candidate_comparison import (
    CandidateComparisonItemResponse,
    CandidateComparisonResponse,
    CoverageCountsResponse,
    ReviewLabel,
)


def _coverage(row: Mapping[str, Any], prefix: str) -> CoverageCountsResponse:
    supported = int(row[f"{prefix}_supported"])
    partial = int(row[f"{prefix}_partial"])
    no_evidence = int(row[f"{prefix}_no_evidence"])
    return CoverageCountsResponse(
        supported=supported,
        partial=partial,
        no_evidence=no_evidence,
        total=supported + partial + no_evidence,
    )


def _review_label(
    required: CoverageCountsResponse,
    preferred: CoverageCountsResponse,
) -> ReviewLabel:
    # Labels describe only visible evidence counts. They never use an LLM or score.
    if required.total > 0 and required.supported == required.total:
        return "strong_evidence"
    if (
        required.supported > 0
        or required.partial > 0
        or (required.total == 0 and preferred.supported > 0)
    ):
        return "moderate_evidence"
    return "needs_verification"


def _evidence_sort_key(item: CandidateComparisonItemResponse) -> tuple[int, ...]:
    assert item.required is not None
    assert item.preferred is not None
    assert item.needs_verification_count is not None
    completed_at = item.latest_completed_at
    return (
        -item.required.supported,
        item.required.no_evidence,
        -item.required.partial,
        -item.preferred.supported,
        item.needs_verification_count,
        -int(completed_at.timestamp()) if completed_at is not None else 0,
        item.candidate_id,
    )


def _comparable_key(item: CandidateComparisonItemResponse) -> tuple[int, ...]:
    assert item.required is not None
    assert item.preferred is not None
    assert item.needs_verification_count is not None
    return (
        item.required.supported,
        item.required.no_evidence,
        item.required.partial,
        item.preferred.supported,
        item.needs_verification_count,
    )


def get_candidate_comparison(
    db: Session, *, job_id: int
) -> CandidateComparisonResponse:
    items: list[CandidateComparisonItemResponse] = []
    for row in candidate_comparison.list_summaries(db, job_id=job_id):
        has_completed = row["latest_completed_run_id"] is not None
        required = _coverage(row, "required") if has_completed else None
        preferred = _coverage(row, "preferred") if has_completed else None
        eligible = row["status"] == CandidateStatus.COMPLETED and has_completed
        items.append(
            CandidateComparisonItemResponse(
                candidate_id=row["candidate_id"],
                name=row["name"],
                email=row["email"],
                original_filename=row["original_filename"],
                status=row["status"],
                created_at=row["created_at"],
                resume_extraction_status=row["resume_extraction_status"],
                latest_completed_run_id=row["latest_completed_run_id"],
                latest_completed_at=row["latest_completed_at"],
                active_screening_run_id=row["active_screening_run_id"],
                active_screening_stage=row["active_screening_stage"],
                active_screening_stage_updated_at=(
                    row["active_screening_stage_updated_at"]
                ),
                required=required,
                preferred=preferred,
                needs_verification_count=(
                    int(row["needs_verification_count"]) if has_completed else None
                ),
                review_priority=None,
                review_label=(
                    _review_label(required, preferred)
                    if eligible and required is not None and preferred is not None
                    else None
                ),
                comparable_evidence=False,
            )
        )

    eligible_items = [
        item
        for item in items
        if item.status == CandidateStatus.COMPLETED
        and item.latest_completed_run_id is not None
    ]
    eligible_items.sort(key=_evidence_sort_key)
    comparable_counts = Counter(_comparable_key(item) for item in eligible_items)
    for priority, item in enumerate(eligible_items, start=1):
        item.review_priority = priority
        item.comparable_evidence = comparable_counts[_comparable_key(item)] > 1

    state_order = {
        CandidateStatus.PROCESSING: 0,
        CandidateStatus.UPLOADED: 1,
        CandidateStatus.FAILED: 2,
        CandidateStatus.COMPLETED: 3,
    }
    unranked_items = [item for item in items if item.review_priority is None]
    unranked_items.sort(
        key=lambda item: (
            state_order[item.status],
            -int(item.created_at.timestamp()),
            item.candidate_id,
        )
    )
    return CandidateComparisonResponse(
        job_id=job_id,
        candidates=[*eligible_items, *unranked_items],
    )
