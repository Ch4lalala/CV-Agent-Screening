"""Validated inputs, intermediate outputs, and report types for screening."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RequirementType = Literal["required", "preferred"]
RequirementSource = Literal["recruiter", "ai_derived"]
EvidenceStatus = Literal["supported", "partial", "no_evidence"]
Confidence = Literal["high", "medium", "low"]


class AgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RecruiterRequirement(AgentModel):
    id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    requirement_type: RequirementType
    priority: int | None = None


class JobRequirementAI(AgentModel):
    source_requirement_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    requirement_type: RequirementType
    source: RequirementSource
    priority: int | None = None
    recruiter_name: str | None = Field(default=None, max_length=255)
    recruiter_description: str | None = Field(default=None, max_length=4000)


class JobRequirementsResponse(AgentModel):
    requirements: list[JobRequirementAI] = Field(default_factory=list, max_length=100)


class CandidateExperience(AgentModel):
    role: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    period: str | None = Field(default=None, max_length=255)
    description: list[str] = Field(default_factory=list, max_length=30)


class CandidateEducation(AgentModel):
    institution: str | None = Field(default=None, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    period: str | None = Field(default=None, max_length=255)


class CandidateProject(AgentModel):
    name: str | None = Field(default=None, max_length=255)
    description: list[str] = Field(default_factory=list, max_length=30)
    technologies: list[str] = Field(default_factory=list, max_length=50)
    url: str | None = Field(default=None, max_length=2048)


class CandidateProfile(AgentModel):
    candidate_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=100)
    work_experience: list[CandidateExperience] = Field(
        default_factory=list, max_length=50
    )
    education: list[CandidateEducation] = Field(default_factory=list, max_length=30)
    projects: list[CandidateProject] = Field(default_factory=list, max_length=50)
    certifications: list[str] = Field(default_factory=list, max_length=50)
    github_urls: list[str] = Field(default_factory=list, max_length=20)
    portfolio_urls: list[str] = Field(default_factory=list, max_length=20)


class EvidenceItem(AgentModel):
    quote: str = Field(min_length=1, max_length=2000)
    source_section: str | None = Field(default=None, max_length=255)
    source_page: int | None = Field(default=None, ge=1)


class EvidenceAssessmentDraft(AgentModel):
    requirement_index: int = Field(ge=0)
    status: EvidenceStatus
    confidence: Confidence
    explanation: str = Field(min_length=1, max_length=4000)
    needs_human_verification: bool
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=20)


class EvidenceAnalysisResponse(AgentModel):
    assessments: list[EvidenceAssessmentDraft] = Field(
        default_factory=list, max_length=100
    )


class EvidenceAssessment(AgentModel):
    requirement_index: int = Field(ge=0)
    source_requirement_id: int | None = None
    requirement: str = Field(min_length=1, max_length=255)
    requirement_type: RequirementType
    requirement_source: RequirementSource
    status: EvidenceStatus
    confidence: Confidence
    explanation: str = Field(min_length=1, max_length=4000)
    needs_human_verification: bool
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=20)


class InterviewQuestionDraft(AgentModel):
    requirement_index: int = Field(ge=0)
    question: str = Field(min_length=10, max_length=1000)


class InterviewQuestionsResponse(AgentModel):
    questions: list[InterviewQuestionDraft] = Field(
        default_factory=list, max_length=10
    )


class InterviewQuestion(AgentModel):
    requirement: str = Field(min_length=1, max_length=255)
    requirement_type: RequirementType
    question: str = Field(min_length=10, max_length=1000)
    reason: str = Field(min_length=1, max_length=4000)


class CoverageSummary(AgentModel):
    supported: int = Field(ge=0)
    total: int = Field(ge=0)


class ScreeningReport(AgentModel):
    job_id: str
    candidate_id: str
    job_title: str = Field(min_length=1, max_length=255)
    normalized_requirements: list[JobRequirementAI]
    candidate_profile: CandidateProfile
    required_coverage: CoverageSummary
    preferred_coverage: CoverageSummary
    evidence_results: list[EvidenceAssessment]
    needs_verification: list[str]
    interview_questions: list[InterviewQuestion]
    security_warning: None = None
