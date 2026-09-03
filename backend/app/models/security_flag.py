from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SecurityFlagType, SecuritySeverity, enum_values

if TYPE_CHECKING:
    from app.models.screening_run import ScreeningRun


class SecurityFlag(Base):
    __tablename__ = "security_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    screening_run_id: Mapped[int] = mapped_column(
        ForeignKey("screening_runs.id", ondelete="CASCADE"),
        index=True,
    )
    flag_type: Mapped[SecurityFlagType] = mapped_column(
        SqlEnum(
            SecurityFlagType,
            name="security_flag_type",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        )
    )
    severity: Mapped[SecuritySeverity] = mapped_column(
        SqlEnum(
            SecuritySeverity,
            name="security_severity",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        )
    )
    detected_text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    excluded_from_evaluation: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    source_page: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    screening_run: Mapped["ScreeningRun"] = relationship(
        back_populates="security_flags"
    )
