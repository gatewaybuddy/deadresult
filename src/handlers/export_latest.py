"""GET /v1/export/latest — presigned URL for most recent export."""
from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

from src.lib.response import success


def handler(event, context):
    s3_bucket = os.environ.get("DEADRESULT_S3_BUCKET", "")
    aws_region = os.environ.get("DEADRESULT_AWS_REGION", "us-east-1")

    s3 = boto3.client("s3", region_name=aws_region)

    try:
        response = s3.list_objects_v2(
            Bucket=s3_bucket,
            Prefix="exports/catalog_",
        )
    except ClientError:
        return success({"url": None, "message": "No exports available yet"})

    contents = response.get("Contents", [])
    if not contents:
        return success({"url": None, "message": "No exports available yet"})

    latest = sorted(contents, key=lambda o: o["LastModified"], reverse=True)[0]

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_bucket, "Key": latest["Key"]},
        ExpiresIn=3600,
    )
    return success({"url": url, "message": "Latest export ready"})
