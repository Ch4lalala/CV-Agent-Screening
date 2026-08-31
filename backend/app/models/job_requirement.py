from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import RequirementType, enum_values

if TYPE_CHECKING:
    from app.models.job import Job


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_type: Mapped[RequirementType] = mapped_column(
        SqlEnum(
            RequirementType,
            name="requirement_type",
            native_enum=False,
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=RequirementType.REQUIRED,
        server_default=RequirementType.REQUIRED.value,
    )
    priority: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    job: Mapped["Job"] = relationship(back_populates="requirements")

