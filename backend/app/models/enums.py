from enum import Enum


class JobStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class RequirementType(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class CandidateStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResumeExtractionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ScreeningRunStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScreeningStage(str, Enum):
    QUEUED = "queued"
    NORMALIZE_REQUIREMENTS = "normalize_requirements"
    RESUME_SECURITY = "resume_security"
    EXTRACT_CANDIDATE_PROFILE = "extract_candidate_profile"
    MATCH_EVIDENCE = "match_evidence"
    ANALYZE_UNCERTAINTY = "analyze_uncertainty"
    GENERATE_INTERVIEW_QUESTIONS = "generate_interview_questions"
    GENERATE_REPORT = "generate_report"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    NO_EVIDENCE = "no_evidence"


class EvidenceConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SecurityStatus(str, Enum):
    CLEAN = "clean"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"


class SecurityFlagType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    INSTRUCTION_MANIPULATION = "instruction_manipulation"
    RANKING_MANIPULATION = "ranking_manipulation"
    EVALUATION_OVERRIDE = "evaluation_override"
    SUSPICIOUS_HIDDEN_INSTRUCTION = "suspicious_hidden_instruction"


class SecuritySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [item.value for item in enum_class]
