"""Publisher entity separation."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0002_publisher_entity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publishers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_publishers_name"),
    )

    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(
            sa.Column("publisher_id", sa.String(length=36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_agents_publisher_id",
            "publishers",
            ["publisher_id"],
            ["id"],
        )

    _backfill_publishers()

    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_column("publisher_name")
        batch_op.drop_column("publisher_title")
        batch_op.drop_column("publisher_verified")


def _backfill_publishers() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, publisher_name, publisher_title, publisher_verified "
            "FROM agents WHERE publisher_name IS NOT NULL AND publisher_name != ''"
        )
    ).fetchall()

    now = sa.func.current_timestamp()
    publisher_ids: dict[str, str] = {}
    for agent_id, pub_name, pub_title, pub_verified in rows:
        if pub_name in publisher_ids:
            publisher_id = publisher_ids[pub_name]
        else:
            publisher_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"publisher-backfill:{pub_name}")
            )
            publisher_ids[pub_name] = publisher_id
            bind.execute(
                sa.text(
                    "INSERT INTO publishers "
                    "(id, name, title, verified, verified_at, verification_note, "
                    "created_at) "
                    "VALUES (:id, :name, :title, :verified, :verified_at, NULL, "
                    ":created_at)"
                ),
                {
                    "id": publisher_id,
                    "name": pub_name,
                    "title": pub_title,
                    "verified": bool(pub_verified),
                    "verified_at": (
                        bind.execute(sa.select(now)).scalar() if pub_verified else None
                    ),
                    "created_at": bind.execute(sa.select(now)).scalar(),
                },
            )
        bind.execute(
            sa.text("UPDATE agents SET publisher_id = :pid WHERE id = :aid"),
            {"pid": publisher_id, "aid": agent_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(
            sa.Column("publisher_name", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("publisher_title", sa.String(length=200), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "publisher_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE agents SET "
            "publisher_name = (SELECT name FROM publishers "
            "WHERE publishers.id = agents.publisher_id), "
            "publisher_title = (SELECT title FROM publishers "
            "WHERE publishers.id = agents.publisher_id), "
            "publisher_verified = COALESCE("
            "(SELECT verified FROM publishers "
            "WHERE publishers.id = agents.publisher_id), 0) "
            "WHERE publisher_id IS NOT NULL"
        )
    )

    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_constraint("fk_agents_publisher_id", type_="foreignkey")
        batch_op.drop_column("publisher_id")

    op.drop_table("publishers")
