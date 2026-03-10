"""API Gateway response helpers."""
from __future__ import annotations

import json
from typing import Any


def success(body: Any, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-API-Key",
        },
        "body": json.dumps(body, default=str),
    }


def error(message: str, status_code: int = 400) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({"detail": message}),
    }
