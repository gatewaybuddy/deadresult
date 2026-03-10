"""GET /v1/stats — aggregated catalog statistics."""
from __future__ import annotations

from sqlalchemy import func, select, text

from src.lib.db import get_session
from src.lib.models import Experiment
from src.lib.response import success


def handler(event, context):
    session = get_session()
    try:
        total = session.execute(select(func.count(Experiment.id))).scalar_one()
        failed = session.execute(
            select(func.count(Experiment.id)).where(Experiment.status == "failed")
        ).scalar_one()
        successful = session.execute(
            select(func.count(Experiment.id)).where(Experiment.status == "success")
        ).scalar_one()
        compute_hours = session.execute(
            select(func.coalesce(func.sum(Experiment.compute_hours), 0.0))
        ).scalar_one()

        ds_query = (
            select(Experiment.dataset_name, func.count(Experiment.id).label("count"))
            .group_by(Experiment.dataset_name)
            .order_by(text("count DESC"))
            .limit(10)
        )
        ds_rows = session.execute(ds_query).all()
        top_datasets = [{"name": r[0], "count": r[1]} for r in ds_rows]

        arch_query = (
            select(Experiment.architecture, func.count(Experiment.id).label("count"))
            .where(Experiment.architecture.is_not(None))
            .group_by(Experiment.architecture)
            .order_by(text("count DESC"))
            .limit(10)
        )
        arch_rows = session.execute(arch_query).all()
        top_architectures = [{"name": r[0], "count": r[1]} for r in arch_rows]

        status_query = (
            select(Experiment.status, func.count(Experiment.id).label("count"))
            .group_by(Experiment.status)
            .order_by(text("count DESC"))
        )
        status_rows = session.execute(status_query).all()
        failure_categories = [{"category": r[0], "count": r[1]} for r in status_rows]

        return success({
            "total_experiments": total,
            "total_failed": failed,
            "total_successful": successful,
            "total_compute_hours_logged": float(compute_hours),
            "top_failure_categories": failure_categories,
            "top_datasets": top_datasets,
            "top_architectures": top_architectures,
        })
    finally:
        session.close()
