"""GET /v1/similar/{id} — find similar experiments via pgvector or heuristic."""
from __future__ import annotations

from sqlalchemy import or_, select

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import error, success
from src.lib.schemas import ExperimentResponse


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    experiment_id = path_params.get("id", "")
    params = event.get("queryStringParameters") or {}

    if not experiment_id:
        return error("Missing experiment ID", 400)

    try:
        limit = min(50, max(1, int(params.get("limit", "10"))))
    except (ValueError, TypeError):
        return error("Invalid limit", 400)

    session = get_session()
    try:
        source = session.get(Experiment, experiment_id)
        if source is None:
            return error("Experiment not found", 404)

        results = []

        if source.embedding is not None:
            dist = Experiment.embedding.cosine_distance(source.embedding).label("distance")
            query = (
                select(Experiment, (1 - dist).label("similarity"))
                .where(Experiment.id != experiment_id)
                .where(Experiment.embedding.is_not(None))
                .order_by(dist)
                .limit(limit)
            )
            rows = session.execute(query).all()
            results = [(row[0], float(row[1])) for row in rows]
        else:
            # Fallback: match by dataset + architecture
            conditions = [
                Experiment.dataset_name == source.dataset_name,
                Experiment.architecture == source.architecture,
            ]
            query = (
                select(Experiment)
                .where(Experiment.id != experiment_id)
                .where(or_(*conditions))
                .order_by(Experiment.created_at.desc())
                .limit(limit)
            )
            rows = session.execute(query).scalars().all()

            for row in rows:
                score = 0.0
                if row.dataset_name == source.dataset_name:
                    score += 0.4
                if row.architecture == source.architecture:
                    score += 0.3
                if source.tags and row.tags:
                    overlap = len(set(source.tags) & set(row.tags))
                    total = len(set(source.tags) | set(row.tags))
                    score += 0.3 * (overlap / total) if total > 0 else 0
                results.append((row, round(score, 3)))

            results.sort(key=lambda x: x[1], reverse=True)

        matches = []
        for exp, sim in results:
            resp = ExperimentResponse.model_validate(exp)
            matches.append({
                "experiment": resp.model_dump(mode="json"),
                "similarity": sim,
                "compute_saved": exp.compute_hours,
            })

        return success({
            "matches": matches,
            "total": len(matches),
            "page": 1,
            "page_size": limit,
        })
    finally:
        session.close()
