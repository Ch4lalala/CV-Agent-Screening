from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.screening_run import ScreeningRun


JSONValue = JSON().with_variant(JSONB(), "postgresql")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    screening_run_id: Mapped[int] = mapped_column(
        ForeignKey("screening_runs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONValue)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    screening_run: Mapped["ScreeningRun"] = relationship(
        back_populates="candidate_profile"
    )
