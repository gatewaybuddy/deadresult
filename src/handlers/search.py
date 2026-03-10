"""GET /v1/search — search experiments with filters and pagination."""
from __future__ import annotations

from sqlalchemy import cast, func, or_, select, String

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import error, success
from src.lib.schemas import ExperimentResponse


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    multi_params = event.get("multiValueQueryStringParameters") or {}

    q = params.get("q")
    dataset = params.get("dataset")
    architecture = params.get("architecture")
    status = params.get("status")
    tags = multi_params.get("tags")

    try:
        page = max(1, int(params.get("page", "1")))
        page_size = min(100, max(1, int(params.get("page_size", "20"))))
    except (ValueError, TypeError):
        return error("Invalid page or page_size", 400)

    session = get_session()
    try:
        query = select(Experiment)
        count_query = select(func.count(Experiment.id))

        if q:
            like_pat = f"%{q}%"
            text_filter = or_(
                Experiment.hypothesis.ilike(like_pat),
                Experiment.notes.ilike(like_pat),
                cast(Experiment.approach, String).ilike(like_pat),
            )
            query = query.where(text_filter)
            count_query = count_query.where(text_filter)

        if dataset:
            query = query.where(Experiment.dataset_name.ilike(f"%{dataset}%"))
            count_query = count_query.where(Experiment.dataset_name.ilike(f"%{dataset}%"))

        if architecture:
            query = query.where(Experiment.architecture.ilike(f"%{architecture}%"))
            count_query = count_query.where(Experiment.architecture.ilike(f"%{architecture}%"))

        if status:
            query = query.where(Experiment.status == status)
            count_query = count_query.where(Experiment.status == status)

        if tags:
            tag_filters = [cast(Experiment.tags, String).ilike(f"%{t}%") for t in tags]
            tag_cond = or_(*tag_filters)
            query = query.where(tag_cond)
            count_query = count_query.where(tag_cond)

        total = session.execute(count_query).scalar_one()

        query = query.order_by(Experiment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = session.execute(query).scalars().all()

        matches = []
        for exp in rows:
            resp = ExperimentResponse.model_validate(exp)
            matches.append({
                "experiment": resp.model_dump(mode="json"),
                "similarity": None,
                "compute_saved": exp.compute_hours,
            })

        return success({
            "matches": matches,
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    finally:
        session.close()
