from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import CandidateStatus, enum_values

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.resume_document import ResumeDocument


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[CandidateStatus] = mapped_column(
        SqlEnum(
            CandidateStatus,
            name="candidate_status",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=CandidateStatus.UPLOADED,
        server_default=CandidateStatus.UPLOADED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship(back_populates="candidates")
    resume_document: Mapped["ResumeDocument | None"] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )

