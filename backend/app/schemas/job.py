from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import JobStatus
from app.schemas.common import OrmResponse


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    status: JobStatus = JobStatus.DRAFT


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    status: JobStatus | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "JobUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class JobResponse(OrmResponse):
    id: int
    user_id: int
    title: str
    description: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime

