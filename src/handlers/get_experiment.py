"""GET /v1/experiments/{id} — fetch a single experiment."""
from __future__ import annotations

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import error, success
from src.lib.schemas import ExperimentResponse


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    experiment_id = path_params.get("id", "")

    if not experiment_id:
        return error("Missing experiment ID", 400)

    session = get_session()
    try:
        exp = session.get(Experiment, experiment_id)
        if exp is None:
            return error("Experiment not found", 404)

        resp = ExperimentResponse.model_validate(exp)
        return success(resp.model_dump(mode="json"))
    finally:
        session.close()
