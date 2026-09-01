"""Add Phase 6 screening persistence tables.

Revision ID: 20260901_0003
Revises: 20260901_0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0003"
down_revision: str | Sequence[str] | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "screening_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "completed",
                "failed",
                name="screening_run_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "report_json",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_screening_runs_candidate_id",
        "screening_runs",
        ["candidate_id"],
    )
    op.create_index(
        "uq_screening_runs_candidate_processing",
        "screening_runs",
        ["candidate_id"],
        unique=True,
        postgresql_where=sa.text("status = 'processing'"),
    )

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "screening_run_id",
            sa.Integer(),
            sa.ForeignKey("screening_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_json",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_candidate_profiles_screening_run_id",
        "candidate_profiles",
        ["screening_run_id"],
        unique=True,
    )

    op.create_table(
        "evidence_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "screening_run_id",
            sa.Integer(),
            sa.ForeignKey("screening_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requirement_id",
            sa.Integer(),
            sa.ForeignKey("job_requirements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requirement_name", sa.String(length=255), nullable=False),
        sa.Column(
            "requirement_type",
            sa.Enum(
                "required",
                "preferred",
                name="evidence_requirement_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "supported",
                "partial",
                "no_evidence",
                name="evidence_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Enum(
                "high",
                "medium",
                "low",
                name="evidence_confidence",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("needs_human_verification", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_results_screening_run_id",
        "evidence_results",
        ["screening_run_id"],
    )
    op.create_index(
        "ix_evidence_results_requirement_id",
        "evidence_results",
        ["requirement_id"],
    )

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "evidence_result_id",
            sa.Integer(),
            sa.ForeignKey("evidence_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("source_section", sa.String(length=255), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_items_evidence_result_id",
        "evidence_items",
        ["evidence_result_id"],
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "screening_run_id",
            sa.Integer(),
            sa.ForeignKey("screening_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_name", sa.String(length=255), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_interview_questions_screening_run_id",
        "interview_questions",
        ["screening_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_interview_questions_screening_run_id",
        table_name="interview_questions",
    )
    op.drop_table("interview_questions")
    op.drop_index("ix_evidence_items_evidence_result_id", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_evidence_results_requirement_id", table_name="evidence_results")
    op.drop_index("ix_evidence_results_screening_run_id", table_name="evidence_results")
    op.drop_table("evidence_results")
    op.drop_index(
        "ix_candidate_profiles_screening_run_id", table_name="candidate_profiles"
    )
    op.drop_table("candidate_profiles")
    op.drop_index("uq_screening_runs_candidate_processing", table_name="screening_runs")
    op.drop_index("ix_screening_runs_candidate_id", table_name="screening_runs")
    op.drop_table("screening_runs")
