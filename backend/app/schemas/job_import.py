from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class JobImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GeneratedJobRequirement(JobImportModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    type: Literal["required", "preferred"]


JobImportWarningType: TypeAlias = Literal[
    "ambiguous_requirement",
    "excluded_personal_criterion",
    "composite_requirement",
    "duplicate_requirement",
    "inferred_title",
    "review_required",
]


class JobImportWarning(JobImportModel):
    type: JobImportWarningType
    message: str = Field(min_length=1, max_length=1000)
    related_text: str | None = Field(default=None, max_length=1000)


class JobDescriptionAnalysisRequest(JobImportModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=20_000)


class JobImportDraft(JobImportModel):
    title: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=1, max_length=20_000)
    requirements: list[GeneratedJobRequirement] = Field(
        default_factory=list,
        max_length=100,
    )
    warnings: list[JobImportWarning] = Field(default_factory=list, max_length=50)
