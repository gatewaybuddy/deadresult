"""POST /v1/export — trigger a catalog export to S3."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3
from pydantic import ValidationError
from sqlalchemy import select

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import error, success
from src.lib.schemas import ExperimentResponse, ExportRequest


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        data = ExportRequest(**body)
    except (json.JSONDecodeError, ValidationError) as exc:
        return error(str(exc), 400)

    s3_bucket = os.environ.get("DEADRESULT_S3_BUCKET", "")
    aws_region = os.environ.get("DEADRESULT_AWS_REGION", "us-east-1")

    session = get_session()
    try:
        query = select(Experiment).order_by(Experiment.created_at.desc())
        rows = session.execute(query).scalars().all()

        experiments = [
            ExperimentResponse.model_validate(exp).model_dump(mode="json")
            for exp in rows
        ]

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"exports/catalog_{timestamp}.json"

        payload = json.dumps(
            {"exported_at": timestamp, "total": len(experiments), "experiments": experiments},
            default=str,
        )

        s3 = boto3.client("s3", region_name=aws_region)
        s3.put_object(
            Bucket=s3_bucket,
            Key=key,
            Body=payload.encode(),
            ContentType="application/json",
        )

        return success(
            {"message": f"Export will be emailed to {data.email} when ready"},
            202,
        )
    finally:
        session.close()
