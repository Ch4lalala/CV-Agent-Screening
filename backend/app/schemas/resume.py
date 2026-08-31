from pydantic import BaseModel

from app.models.enums import ResumeExtractionStatus


class ResumeSummaryResponse(BaseModel):
    page_count: int
    extraction_status: ResumeExtractionStatus
    text_length: int
    message: str | None = None


class ResumeMetadataResponse(ResumeSummaryResponse):
    original_filename: str

