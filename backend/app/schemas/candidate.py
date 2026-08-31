from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import CandidateStatus
from app.schemas.common import OrmResponse


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    status: CandidateStatus = CandidateStatus.UPLOADED


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    status: CandidateStatus | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "CandidateUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CandidateResponse(OrmResponse):
    id: int
    job_id: int
    name: str
    email: EmailStr
    original_filename: str | None
    resume_path: str | None
    status: CandidateStatus
    created_at: datetime
    updated_at: datetime

