"""SQLAlchemy ORM models for Lambda handlers.

Mirrors deadresult/models/experiment.py but uses sync Base from src.lib.db.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Index, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base

EMBEDDING_DIM = 384


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"exp_{uuid.uuid4().hex[:16]}"


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=text("now()")
    )

    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    approach: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dataset: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hardware: Mapped[dict] = mapped_column(JSONB, nullable=True)
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    submitter: Mapped[dict] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    architecture: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    code_diff_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    compute_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )

    __table_args__ = (
        Index("ix_experiments_tags", "tags", postgresql_using="gin"),
        Index(
            "ix_experiments_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
