"""Add persisted screening stage progress.

Revision ID: 20260902_0004
Revises: 20260901_0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260902_0004"
down_revision: str | Sequence[str] | None = "20260901_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STAGES = (
    "queued",
    "normalize_requirements",
    "extract_candidate_profile",
    "match_evidence",
    "analyze_uncertainty",
    "generate_interview_questions",
    "generate_report",
    "completed",
    "failed",
)


def upgrade() -> None:
    op.add_column(
        "screening_runs",
        sa.Column(
            "current_stage",
            sa.String(length=36),
            server_default="queued",
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE screening_runs SET current_stage = CASE "
        "WHEN status = 'completed' THEN 'completed' "
        "WHEN status = 'failed' THEN 'failed' "
        "ELSE 'queued' END"
    )
    quoted = ", ".join(f"'{stage}'" for stage in _STAGES)
    op.create_check_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        f"current_stage IN ({quoted})",
    )
    op.add_column(
        "screening_runs",
        sa.Column(
            "current_stage_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("screening_runs", "current_stage_updated_at")
    op.drop_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        type_="check",
    )
    op.drop_column("screening_runs", "current_stage")
