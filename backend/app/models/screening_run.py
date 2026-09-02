from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ScreeningRunStatus, ScreeningStage, enum_values

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.candidate_profile import CandidateProfile
    from app.models.evidence_result import EvidenceResult
    from app.models.interview_question import InterviewQuestion


JSONValue = JSON().with_variant(JSONB(), "postgresql")


class ScreeningRun(Base):
    __tablename__ = "screening_runs"
    __table_args__ = (
        Index(
            "uq_screening_runs_candidate_processing",
            "candidate_id",
            unique=True,
            postgresql_where=text("status = 'processing'"),
            sqlite_where=text("status = 'processing'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ScreeningRunStatus] = mapped_column(
        SqlEnum(
            ScreeningRunStatus,
            name="screening_run_status",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=ScreeningRunStatus.PENDING,
        server_default=ScreeningRunStatus.PENDING.value,
    )
    current_stage: Mapped[ScreeningStage] = mapped_column(
        SqlEnum(
            ScreeningStage,
            name="screening_stage",
            native_enum=False,
            create_constraint=True,
            length=36,
            values_callable=enum_values,
        ),
        default=ScreeningStage.QUEUED,
        server_default=ScreeningStage.QUEUED.value,
    )
    current_stage_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSONValue, nullable=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="screening_runs")
    candidate_profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="screening_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    evidence_results: Mapped[list["EvidenceResult"]] = relationship(
        back_populates="screening_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    interview_questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="screening_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
