from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import JobStatus, enum_values

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job_requirement import JobRequirement
    from app.models.user import User


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(
        SqlEnum(
            JobStatus,
            name="job_status",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=JobStatus.DRAFT,
        server_default=JobStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="jobs")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

