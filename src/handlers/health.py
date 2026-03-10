"""GET /health — simple health check, no database."""
from __future__ import annotations

from src.lib.response import success


def handler(event, context):
    return success({"status": "ok"})
