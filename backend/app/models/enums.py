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


def enum_values(enum_class: type[Enum]) -> list[str]:
    return [item.value for item in enum_class]
