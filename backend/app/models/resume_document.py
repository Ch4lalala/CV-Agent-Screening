from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ResumeExtractionStatus, enum_values

if TYPE_CHECKING:
    from app.models.candidate import Candidate


class ResumeDocument(Base):
    __tablename__ = "resume_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int] = mapped_column(default=0, server_default="0")
    extraction_status: Mapped[ResumeExtractionStatus] = mapped_column(
        SqlEnum(
            ResumeExtractionStatus,
            name="resume_extraction_status",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=ResumeExtractionStatus.PENDING,
        server_default=ResumeExtractionStatus.PENDING.value,
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="resume_document")

