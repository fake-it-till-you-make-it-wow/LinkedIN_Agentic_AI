"""GitHub layer — github_repo/star_count on agents + agent_releases table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_github_layer"
down_revision = "0003_review_entity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agents") as batch:
        batch.add_column(
            sa.Column("github_repo", sa.String(length=120), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "github_star_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    op.create_table(
        "agent_releases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["agents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "tag", name="uq_agent_releases_agent_id_tag"),
    )
    op.create_index("ix_agent_releases_agent_id", "agent_releases", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_releases_agent_id", table_name="agent_releases")
    op.drop_table("agent_releases")
    with op.batch_alter_table("agents") as batch:
        batch.drop_column("github_star_count")
        batch.drop_column("github_repo")
