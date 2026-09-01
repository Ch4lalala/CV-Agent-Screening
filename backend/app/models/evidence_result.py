from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    EvidenceConfidence,
    EvidenceStatus,
    RequirementType,
    enum_values,
)

if TYPE_CHECKING:
    from app.models.evidence_item import EvidenceItem
    from app.models.job_requirement import JobRequirement
    from app.models.screening_run import ScreeningRun


class EvidenceResult(Base):
    __tablename__ = "evidence_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    screening_run_id: Mapped[int] = mapped_column(
        ForeignKey("screening_runs.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    requirement_name: Mapped[str] = mapped_column(String(255))
    requirement_type: Mapped[RequirementType] = mapped_column(
        SqlEnum(
            RequirementType,
            name="evidence_requirement_type",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        )
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        SqlEnum(
            EvidenceStatus,
            name="evidence_status",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        )
    )
    confidence: Mapped[EvidenceConfidence] = mapped_column(
        SqlEnum(
            EvidenceConfidence,
            name="evidence_confidence",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        )
    )
    explanation: Mapped[str] = mapped_column(Text)
    needs_human_verification: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    screening_run: Mapped["ScreeningRun"] = relationship(
        back_populates="evidence_results"
    )
    requirement: Mapped["JobRequirement | None"] = relationship(
        back_populates="evidence_results"
    )
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        back_populates="evidence_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
