"""Add secure resume extraction persistence.

Revision ID: 20260901_0002
Revises: 20260831_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260901_0002"
down_revision: str | Sequence[str] | None = "20260831_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("candidates", "name", existing_type=sa.String(255), nullable=True)
    op.alter_column("candidates", "email", existing_type=sa.String(320), nullable=True)

    op.create_table(
        "resume_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "extraction_status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                name="resume_extraction_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_resume_documents_candidate_id",
        "resume_documents",
        ["candidate_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_resume_documents_candidate_id", table_name="resume_documents")
    op.drop_table("resume_documents")
    op.alter_column("candidates", "email", existing_type=sa.String(320), nullable=False)
    op.alter_column("candidates", "name", existing_type=sa.String(255), nullable=False)

