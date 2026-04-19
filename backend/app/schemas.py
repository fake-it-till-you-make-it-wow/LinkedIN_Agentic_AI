"""Pydantic schemas for API and service responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublisherCreate(BaseModel):
    """Publisher creation payload."""

    name: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=200)


class PublisherRead(BaseModel):
    """Publisher response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    title: str | None
    verified: bool
    verified_at: datetime | None
    verification_note: str | None
    created_at: datetime


class PublisherVerifyRequest(BaseModel):
    """Publisher verification payload."""

    note: str | None = Field(default=None, max_length=1000)


class AgentBase(BaseModel):
    """Base fields shared by agent payloads."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    skill_tags: list[str] = Field(default_factory=list)
    endpoint_url: str | None = None
    career_projects: str | None = None
    publisher_id: str | None = None
    version: str = "1.0.0"
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    verified: bool = False
    star_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    avg_response_ms: int = Field(default=1000, ge=0)
    total_calls: int = Field(default=0, ge=0)
    github_repo: str | None = Field(default=None, max_length=120)
    github_star_count: int = Field(default=0, ge=0)


class AgentCreate(AgentBase):
    """Agent creation payload."""


class AgentUpdate(BaseModel):
    """Agent update payload."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    skill_tags: list[str] | None = None
    endpoint_url: str | None = None
    career_projects: str | None = None
    publisher_id: str | None = None
    version: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    verified: bool | None = None
    star_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    success_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    avg_response_ms: int | None = Field(default=None, ge=0)
    total_calls: int | None = Field(default=None, ge=0)
    github_repo: str | None = Field(default=None, max_length=120)
    github_star_count: int | None = Field(default=None, ge=0)


class AgentRead(AgentBase):
    """Agent response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    trust_score: float
    community_score: float
    publisher: PublisherRead | None = None


class SearchAgentResult(AgentRead):
    """Search result payload."""

    specialization_match: float
    semantic_score: float = 0.0
    final_score: float


class MessageRead(BaseModel):
    """Message response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    thread_id: str
    sender_id: str
    content: str
    created_at: datetime


class ThreadRead(BaseModel):
    """Thread detail payload."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    initiator_id: str
    target_id: str
    subject: str
    created_at: datetime
    messages: list[MessageRead]


class ThreadSummary(BaseModel):
    """Thread list payload."""

    thread_id: str
    subject: str
    created_at: datetime
    other_agent: AgentRead
    last_message: MessageRead | None


class InvokeResult(BaseModel):
    """Invoke tool result."""

    invoke_log_id: str
    output: dict[str, Any] | None
    status: str
    response_ms: int


class OutreachResult(BaseModel):
    """Outreach tool result."""

    thread_id: str
    response: str
    status: str


class ReviewResult(BaseModel):
    """Review tool result."""

    success: bool
    new_star_rating: float | None = None
    error: str | None = None


class AgentStats(BaseModel):
    """Per-agent operational metrics derived from InvokeLog + Review."""

    agent_id: str
    total_invocations: int
    success_count: int
    error_count: int
    timeout_count: int
    success_rate: float
    avg_response_ms: int | None
    review_count: int
    star_rating: float
    last_invoked_at: datetime | None
    status: str


class AdminHealth(BaseModel):
    """Aggregate system health for operators."""

    agents_total: int
    agents_verified: int
    publishers_total: int
    publishers_verified: int
    invocations_total: int
    invocation_error_rate: float
    reviews_total: int
    status: str


class SearchWeights(BaseModel):
    """Search scoring weights."""

    star_rating: float = 0.35
    success_rate: float = 0.25
    response_speed: float = 0.2
    specialization: float = 0.1
    semantic: float = 0.1

    @field_validator("*")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        """Prevent negative weights."""

        if value < 0:
            raise ValueError("weights must be non-negative")
        return value
