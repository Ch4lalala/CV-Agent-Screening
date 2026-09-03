from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import (
    CandidateStatus,
    ResumeExtractionStatus,
    ScreeningStage,
    SecurityStatus,
)


ReviewLabel = Literal[
    "strong_evidence",
    "moderate_evidence",
    "needs_verification",
]


class CoverageCountsResponse(BaseModel):
    supported: int
    partial: int
    no_evidence: int
    total: int


class CandidateComparisonItemResponse(BaseModel):
    candidate_id: int
    name: str | None
    email: str | None
    original_filename: str | None
    status: CandidateStatus
    created_at: datetime
    resume_extraction_status: ResumeExtractionStatus | None
    latest_completed_run_id: int | None
    latest_completed_at: datetime | None
    security_status: SecurityStatus | None
    active_screening_run_id: int | None
    active_screening_stage: ScreeningStage | None
    active_screening_stage_updated_at: datetime | None
    required: CoverageCountsResponse | None
    preferred: CoverageCountsResponse | None
    needs_verification_count: int | None
    review_priority: int | None
    review_label: ReviewLabel | None
    comparable_evidence: bool


class CandidateComparisonResponse(BaseModel):
    job_id: int
    candidates: list[CandidateComparisonItemResponse]
