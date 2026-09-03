from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.agents.schemas import CandidateProfile, CoverageSummary, JobRequirementAI
from app.models.enums import (
    CandidateStatus,
    EvidenceConfidence,
    EvidenceStatus,
    RequirementType,
    ScreeningRunStatus,
    ScreeningStage,
    SecurityFlagType,
    SecuritySeverity,
    SecurityStatus,
)


class ScreeningResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ScreeningRunResponse(ScreeningResponseModel):
    id: int
    candidate_id: int
    status: ScreeningRunStatus
    current_stage: ScreeningStage
    current_stage_updated_at: datetime
    model_name: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    security_status: SecurityStatus
    created_at: datetime


class ScreeningStartResponse(ScreeningResponseModel):
    screening_run_id: int
    candidate_id: int
    status: ScreeningRunStatus
    current_stage: ScreeningStage


class CandidateReportCandidateResponse(ScreeningResponseModel):
    id: int
    name: str | None
    email: str | None
    status: CandidateStatus


class ScreeningCoverageResponse(ScreeningResponseModel):
    required: CoverageSummary
    preferred: CoverageSummary


class EvidenceItemResponse(ScreeningResponseModel):
    id: int
    quote: str
    source_section: str | None
    source_page: int | None
    created_at: datetime


class EvidenceResultResponse(ScreeningResponseModel):
    id: int
    requirement_id: int | None
    requirement_name: str
    requirement_type: RequirementType
    status: EvidenceStatus
    confidence: EvidenceConfidence
    explanation: str
    needs_human_verification: bool
    evidence_items: list[EvidenceItemResponse]
    created_at: datetime


class InterviewQuestionResponse(ScreeningResponseModel):
    id: int
    requirement_name: str | None
    question: str
    created_at: datetime


class SecurityFlagResponse(ScreeningResponseModel):
    id: int
    flag_type: SecurityFlagType
    severity: SecuritySeverity
    detected_text: str
    explanation: str
    excluded_from_evaluation: bool
    source_page: int | None
    created_at: datetime


class SecurityAnalysisResponse(BaseModel):
    status: SecurityStatus
    flag_count: int
    flags: list[SecurityFlagResponse]


class CandidateReportResponse(ScreeningResponseModel):
    screening_run: ScreeningRunResponse
    candidate: CandidateReportCandidateResponse
    job_title: str
    normalized_requirements: list[JobRequirementAI]
    candidate_profile: CandidateProfile
    coverage: ScreeningCoverageResponse
    evidence_results: list[EvidenceResultResponse]
    needs_verification: list[str]
    interview_questions: list[InterviewQuestionResponse]
    security: SecurityAnalysisResponse
