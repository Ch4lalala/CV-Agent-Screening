from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RequirementType
from app.schemas.common import OrmResponse


class JobRequirementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    requirement_type: RequirementType = RequirementType.REQUIRED
    priority: int | None = Field(default=None, ge=0)


class JobRequirementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    requirement_type: RequirementType | None = None
    priority: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reject_invalid_nulls(self) -> "JobRequirementUpdate":
        required_fields = {"name", "requirement_type"}
        for field_name in self.model_fields_set & required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class JobRequirementResponse(OrmResponse):
    id: int
    job_id: int
    name: str
    description: str | None
    requirement_type: RequirementType
    priority: int | None
    created_at: datetime

