from __future__ import annotations

import json
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deadresult.config import settings
from deadresult.models.experiment import Experiment
from deadresult.schemas.experiment import ExperimentResponse


def _s3_client():
    return boto3.client("s3", region_name=settings.aws_region)


async def export_catalog_to_s3(db: AsyncSession) -> str:
    """Dump all experiments to S3 as a JSON file. Returns the S3 key."""
    query = select(Experiment).order_by(Experiment.created_at.desc())
    rows = (await db.execute(query)).scalars().all()

    experiments = [
        ExperimentResponse.model_validate(exp).model_dump(mode="json") for exp in rows
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"exports/catalog_{timestamp}.json"

    payload = json.dumps(
        {"exported_at": timestamp, "total": len(experiments), "experiments": experiments},
        default=str,
    )

    s3 = _s3_client()
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=payload.encode(),
        ContentType="application/json",
    )

    return key


def get_latest_export_url() -> str | None:
    """Get a presigned URL for the most recent export file."""
    s3 = _s3_client()

    try:
        response = s3.list_objects_v2(
            Bucket=settings.s3_bucket,
            Prefix="exports/catalog_",
        )
    except ClientError:
        return None

    contents = response.get("Contents", [])
    if not contents:
        return None

    # Sort by LastModified descending, pick most recent
    latest = sorted(contents, key=lambda o: o["LastModified"], reverse=True)[0]

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": latest["Key"]},
        ExpiresIn=3600,
    )
    return url
