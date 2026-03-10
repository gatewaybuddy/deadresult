"""POST /v1/experiments — create a new experiment."""
from __future__ import annotations

import json

from pydantic import ValidationError

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import error, success
from src.lib.schemas import ExperimentCreate, ExperimentResponse


def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        data = ExperimentCreate(**body)
    except (json.JSONDecodeError, ValidationError) as exc:
        return error(str(exc), 400)

    session = get_session()
    try:
        exp = Experiment(
            hypothesis=data.hypothesis,
            approach=data.approach.model_dump(),
            dataset=data.dataset.model_dump(),
            hardware=data.hardware.model_dump() if data.hardware else None,
            results=data.results.model_dump(),
            submitter=data.submitter.model_dump() if data.submitter else None,
            status=data.results.status,
            dataset_name=data.dataset.name,
            architecture=data.approach.model_architecture,
            tags=data.tags,
            notes=data.notes,
            code_hash=data.code_hash,
            code_diff_url=data.code_diff_url,
            compute_hours=data.hardware.compute_hours if data.hardware else None,
        )
        session.add(exp)
        session.commit()
        session.refresh(exp)

        resp = ExperimentResponse.model_validate(exp)
        return success(resp.model_dump(mode="json"), 201)
    finally:
        session.close()
