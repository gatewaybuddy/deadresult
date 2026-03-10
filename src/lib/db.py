"""Sync SQLAlchemy engine/session for Lambda handlers.

Uses psycopg2 (not asyncpg) — simpler for Lambda's request-response model.
Connection is reused across warm invocations via module-level caching.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase


def _get_database_url() -> str:
    url = os.environ.get("DEADRESULT_DATABASE_URL_SYNC", "")
    if not url:
        raise RuntimeError("DEADRESULT_DATABASE_URL_SYNC not set")
    return url


# Module-level engine — reused across warm Lambda invocations
_engine = None
_SessionLocal = None


def _init():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(
            _get_database_url(),
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session() -> Session:
    _init()
    return _SessionLocal()
