from __future__ import annotations

from sqlalchemy import cast, func, or_, select, text, String
from sqlalchemy.ext.asyncio import AsyncSession

from deadresult.models.experiment import Experiment
from deadresult.schemas.experiment import ExperimentCreate


async def create_experiment(db: AsyncSession, data: ExperimentCreate) -> Experiment:
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
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


async def get_experiment(db: AsyncSession, experiment_id: str) -> Experiment | None:
    return await db.get(Experiment, experiment_id)


async def search_experiments(
    db: AsyncSession,
    *,
    q: str | None = None,
    dataset: str | None = None,
    architecture: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Experiment], int]:
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
        # Tags stored as JSON array — use LIKE on the cast to string for portability
        tag_filters = [cast(Experiment.tags, String).ilike(f"%{t}%") for t in tags]
        tag_cond = or_(*tag_filters)
        query = query.where(tag_cond)
        count_query = count_query.where(tag_cond)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Experiment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return list(rows), total


async def find_similar(
    db: AsyncSession,
    experiment_id: str,
    *,
    limit: int = 10,
) -> list[tuple[Experiment, float]]:
    """Find similar experiments using pgvector cosine distance.

    Falls back to tag/dataset overlap heuristic when embeddings aren't available.
    """
    source = await db.get(Experiment, experiment_id)
    if source is None:
        return []

    if source.embedding is not None:
        # pgvector cosine similarity: 1 - cosine_distance
        dist = Experiment.embedding.cosine_distance(source.embedding).label("distance")
        query = (
            select(Experiment, (1 - dist).label("similarity"))
            .where(Experiment.id != experiment_id)
            .where(Experiment.embedding.is_not(None))
            .order_by(dist)
            .limit(limit)
        )
        results = (await db.execute(query)).all()
        return [(row[0], float(row[1])) for row in results]

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
    rows = (await db.execute(query)).scalars().all()

    # Compute rough similarity score
    results: list[tuple[Experiment, float]] = []
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
    return results


async def get_stats(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count(Experiment.id)))).scalar_one()
    failed = (
        await db.execute(
            select(func.count(Experiment.id)).where(Experiment.status == "failed")
        )
    ).scalar_one()
    successful = (
        await db.execute(
            select(func.count(Experiment.id)).where(Experiment.status == "success")
        )
    ).scalar_one()
    compute_hours = (
        await db.execute(select(func.coalesce(func.sum(Experiment.compute_hours), 0.0)))
    ).scalar_one()

    # Top datasets
    ds_query = (
        select(Experiment.dataset_name, func.count(Experiment.id).label("count"))
        .group_by(Experiment.dataset_name)
        .order_by(text("count DESC"))
        .limit(10)
    )
    ds_rows = (await db.execute(ds_query)).all()
    top_datasets = [{"name": r[0], "count": r[1]} for r in ds_rows]

    # Top architectures
    arch_query = (
        select(Experiment.architecture, func.count(Experiment.id).label("count"))
        .where(Experiment.architecture.is_not(None))
        .group_by(Experiment.architecture)
        .order_by(text("count DESC"))
        .limit(10)
    )
    arch_rows = (await db.execute(arch_query)).all()
    top_architectures = [{"name": r[0], "count": r[1]} for r in arch_rows]

    # Top failure categories (status breakdown)
    status_query = (
        select(Experiment.status, func.count(Experiment.id).label("count"))
        .group_by(Experiment.status)
        .order_by(text("count DESC"))
    )
    status_rows = (await db.execute(status_query)).all()
    failure_categories = [{"category": r[0], "count": r[1]} for r in status_rows]

    return {
        "total_experiments": total,
        "total_failed": failed,
        "total_successful": successful,
        "total_compute_hours_logged": float(compute_hours),
        "top_failure_categories": failure_categories,
        "top_datasets": top_datasets,
        "top_architectures": top_architectures,
    }
