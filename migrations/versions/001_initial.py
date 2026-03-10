"""Initial schema — experiments table with pgvector.

Revision ID: 001
Revises:
Create Date: 2024-12-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "experiments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("approach", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("dataset", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("hardware", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("results", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("submitter", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("dataset_name", sa.String(256), nullable=False),
        sa.Column("architecture", sa.String(256), nullable=True),
        sa.Column("tags", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("code_hash", sa.String(128), nullable=True),
        sa.Column("code_diff_url", sa.Text(), nullable=True),
        sa.Column("compute_hours", sa.Float(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
    )

    op.create_index("ix_experiments_status", "experiments", ["status"])
    op.create_index("ix_experiments_dataset_name", "experiments", ["dataset_name"])
    op.create_index("ix_experiments_architecture", "experiments", ["architecture"])
    op.create_index("ix_experiments_tags", "experiments", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_table("experiments")
    op.execute("DROP EXTENSION IF EXISTS vector")
