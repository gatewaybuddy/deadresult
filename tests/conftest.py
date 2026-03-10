"""Test fixtures — uses SQLite in-memory for fast, isolated tests.

The Experiment model uses pgvector (Vector column) and PostgreSQL ARRAY,
which don't work natively in SQLite. We handle this by creating the table
manually with SQLite-compatible types (TEXT for embedding, JSON for tags).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, DateTime, Float, MetaData, String, Table, Text, event, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from deadresult.database import get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _create_sqlite_tables(connection):
    """Create experiment table with SQLite-compatible schema."""
    meta = MetaData()
    Table(
        "experiments",
        meta,
        Column("id", String(64), primary_key=True),
        Column("created_at", DateTime),
        Column("updated_at", DateTime),
        Column("hypothesis", Text, nullable=False),
        Column("notes", Text, nullable=True),
        Column("approach", JSON, nullable=False),
        Column("dataset", JSON, nullable=False),
        Column("hardware", JSON, nullable=True),
        Column("results", JSON, nullable=False),
        Column("submitter", JSON, nullable=True),
        Column("status", String(32), nullable=False),
        Column("dataset_name", String(256), nullable=False),
        Column("architecture", String(256), nullable=True),
        Column("tags", JSON, nullable=True),
        Column("code_hash", String(128), nullable=True),
        Column("code_diff_url", Text, nullable=True),
        Column("compute_hours", Float, nullable=True),
        Column("embedding", Text, nullable=True),  # TEXT stand-in for pgvector Vector
    )
    meta.create_all(connection)


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(_create_sqlite_tables)

    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    from deadresult.api.app import app

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


SAMPLE_EXPERIMENT = {
    "hypothesis": "Rotary positional embeddings with 4 layers should improve perplexity on TinyStories",
    "approach": {
        "model_architecture": "transformer",
        "modifications": ["rotary_embeddings", "depth_4"],
        "training_approach": "standard_sgd",
        "hyperparameters": {"learning_rate": 0.001, "batch_size": 32},
    },
    "dataset": {"name": "TinyStories", "size": "61M tokens", "preprocessing": "standard"},
    "hardware": {"gpu": "RTX 4090", "memory": "24GB", "compute_hours": 4.2},
    "results": {
        "status": "failed",
        "final_perplexity": 3.47,
        "baseline_perplexity": 3.12,
        "convergence": "slow",
        "max_epochs_reached": True,
    },
    "submitter": {"agent_id": "test_agent_001", "verified": True, "reputation_score": 0.94},
    "tags": ["language_model", "positional_encoding", "small_scale"],
    "notes": "Convergence 3x slower than baseline.",
    "code_hash": "sha256:abc123",
}

SAMPLE_EXPERIMENT_2 = {
    "hypothesis": "Adding layer normalization before attention improves training stability on CIFAR-10",
    "approach": {
        "model_architecture": "vision_transformer",
        "modifications": ["pre_norm", "layer_norm"],
        "training_approach": "cosine_annealing",
        "hyperparameters": {"learning_rate": 0.0003, "batch_size": 128},
    },
    "dataset": {"name": "CIFAR-10", "size": "60k images"},
    "hardware": {"gpu": "A100", "memory": "40GB", "compute_hours": 8.5},
    "results": {"status": "success", "metrics": {"accuracy": 0.92}},
    "tags": ["vision", "normalization"],
}

SAMPLE_EXPERIMENT_3 = {
    "hypothesis": "Rotary embeddings with 8 layers on TinyStories should converge faster",
    "approach": {
        "model_architecture": "transformer",
        "modifications": ["rotary_embeddings", "depth_8"],
        "hyperparameters": {"learning_rate": 0.001},
    },
    "dataset": {"name": "TinyStories", "size": "61M tokens"},
    "results": {"status": "failed", "convergence": "very_slow"},
    "tags": ["language_model", "positional_encoding"],
    "notes": "Even worse than depth_4.",
}
