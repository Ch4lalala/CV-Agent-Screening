"""Persist per-run resume security analysis and flags.

Revision ID: 20260903_0005
Revises: 20260902_0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260903_0005"
down_revision: str | Sequence[str] | None = "20260902_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STAGES = (
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
_STAGES = (
    "queued",
    "normalize_requirements",
    "resume_security",
    "extract_candidate_profile",
    "match_evidence",
    "analyze_uncertainty",
    "generate_interview_questions",
    "generate_report",
    "completed",
    "failed",
)


def _stage_constraint(stages: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{stage}'" for stage in stages)
    return f"current_stage IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        _stage_constraint(_STAGES),
    )
    op.add_column(
        "screening_runs",
        sa.Column(
            "security_status",
            sa.Enum(
                "clean",
                "warning",
                "unavailable",
                name="security_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="unavailable",
            nullable=False,
        ),
    )
    op.add_column(
        "screening_runs",
        sa.Column("sanitized_resume_text", sa.Text(), nullable=True),
    )
    op.create_table(
        "security_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "screening_run_id",
            sa.Integer(),
            sa.ForeignKey("screening_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "flag_type",
            sa.Enum(
                "prompt_injection",
                "instruction_manipulation",
                "ranking_manipulation",
                "evaluation_override",
                "suspicious_hidden_instruction",
                name="security_flag_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="security_severity",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("detected_text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "excluded_from_evaluation",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_security_flags_screening_run_id",
        "security_flags",
        ["screening_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_flags_screening_run_id",
        table_name="security_flags",
    )
    op.drop_table("security_flags")
    op.drop_column("screening_runs", "sanitized_resume_text")
    op.drop_column("screening_runs", "security_status")
    op.execute(
        "UPDATE screening_runs SET current_stage = 'extract_candidate_profile' "
        "WHERE current_stage = 'resume_security'"
    )
    op.drop_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_screening_runs_current_stage",
        "screening_runs",
        _stage_constraint(_OLD_STAGES),
    )
