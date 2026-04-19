"""SQLAlchemy ORM models."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


def new_uuid() -> str:
    """Return a UUID string."""

    return str(uuid.uuid4())


class Publisher(Base):
    """Publisher entity — a human expert who backs one or more agents."""

    __tablename__ = "publishers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    verification_note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    agents: Mapped[list[Agent]] = relationship(back_populates="publisher")


class Agent(Base):
    """Registered agent profile."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    skill_tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON), default=list
    )
    endpoint_url: Mapped[str | None] = mapped_column(String(500), default=None)
    career_projects: Mapped[str | None] = mapped_column(Text, default=None)
    publisher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("publishers.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    star_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    avg_response_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    total_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    github_repo: Mapped[str | None] = mapped_column(String(120), default=None)
    github_star_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    publisher: Mapped[Publisher | None] = relationship(back_populates="agents")
    releases: Mapped[list[AgentRelease]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentRelease.published_at.desc()",
    )
    initiated_threads: Mapped[list[Thread]] = relationship(
        back_populates="initiator",
        foreign_keys="Thread.initiator_id",
    )
    targeted_threads: Mapped[list[Thread]] = relationship(
        back_populates="target",
        foreign_keys="Thread.target_id",
    )
    sent_messages: Mapped[list[Message]] = relationship(back_populates="sender")

    @property
    def publisher_verified(self) -> bool:
        """True iff the linked publisher is verified."""

        return self.publisher is not None and self.publisher.verified

    @property
    def trust_score(self) -> float:
        """Compute trust score from static Phase 1 metrics."""

        speed = 1 - min(self.avg_response_ms / 5000, 1.0)
        score = (
            0.4 * (self.star_rating / 5)
            + 0.3 * self.success_rate
            + 0.2 * speed
            + 0.05 * int(self.verified)
            + 0.05 * int(self.publisher_verified)
        )
        return round(score, 4)

    @property
    def community_score(self) -> float:
        """Saturate GitHub star count to [0, 1] on a log scale (Phase 3-B)."""

        if self.github_star_count <= 0:
            return 0.0
        score = math.log1p(self.github_star_count) / math.log1p(100)
        return round(min(1.0, max(0.0, score)), 4)


class Thread(Base):
    """Outreach thread between two agents."""

    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    initiator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    initiator: Mapped[Agent] = relationship(
        back_populates="initiated_threads",
        foreign_keys=[initiator_id],
    )
    target: Mapped[Agent] = relationship(
        back_populates="targeted_threads",
        foreign_keys=[target_id],
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """Message stored under a thread."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("threads.id", ondelete="CASCADE")
    )
    sender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    thread: Mapped[Thread] = relationship(back_populates="messages")
    sender: Mapped[Agent] = relationship(back_populates="sent_messages")


class InvokeLog(Base):
    """Log record for invoke calls."""

    __tablename__ = "invoke_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    caller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class Review(Base):
    """Rating + comment left by one agent for another."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    caller_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id"), nullable=False
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )


class AgentRelease(Base):
    """Release record for an Agent's linked GitHub repository (Phase 3-B)."""

    __tablename__ = "agent_releases"
    __table_args__ = (
        UniqueConstraint("agent_id", "tag", name="uq_agent_releases_agent_id_tag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), default=None)
    body: Mapped[str | None] = mapped_column(Text, default=None)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    agent: Mapped[Agent] = relationship(back_populates="releases")
