"""Review entity promotion."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_review_entity"
down_revision = "0002_publisher_entity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("caller_id", sa.String(length=36), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["caller_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_target_id", "reviews", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_target_id", table_name="reviews")
    op.drop_table("reviews")
