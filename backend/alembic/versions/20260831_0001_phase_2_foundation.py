"""Create Phase 2 persistence tables.

Revision ID: 20260831_0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
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
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "closed",
                name="job_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="draft",
            nullable=False,
        ),
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
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])

    op.create_table(
        "job_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "requirement_type",
            sa.Enum(
                "required",
                "preferred",
                name="requirement_type",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="required",
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_job_requirements_job_id", "job_requirements", ["job_id"]
    )

    op.create_table(
        "candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("resume_path", sa.String(length=1024), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded",
                "processing",
                "completed",
                "failed",
                name="candidate_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="uploaded",
            nullable=False,
        ),
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
    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.create_index("ix_candidates_job_id", "candidates", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_candidates_job_id", table_name="candidates")
    op.drop_index("ix_candidates_email", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index("ix_job_requirements_job_id", table_name="job_requirements")
    op.drop_table("job_requirements")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

