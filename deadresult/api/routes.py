from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from deadresult.database import get_db
from deadresult.schemas.experiment import (
    ExperimentCreate,
    ExperimentListResponse,
    ExperimentResponse,
    SearchResponse,
    SearchResult,
    StatsResponse,
)
from deadresult.services import experiments as svc

router = APIRouter(prefix="/v1")

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def submit_experiment(data: ExperimentCreate, db: DB) -> ExperimentResponse:
    exp = await svc.create_experiment(db, data)
    return ExperimentResponse.model_validate(exp)


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str, db: DB) -> ExperimentResponse:
    exp = await svc.get_experiment(db, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.model_validate(exp)


@router.get("/search", response_model=SearchResponse)
async def search_experiments(
    db: DB,
    q: str | None = None,
    dataset: str | None = None,
    architecture: str | None = None,
    status: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    rows, total = await svc.search_experiments(
        db,
        q=q,
        dataset=dataset,
        architecture=architecture,
        status=status,
        tags=tags,
        page=page,
        page_size=page_size,
    )
    matches = [
        SearchResult(
            experiment=ExperimentResponse.model_validate(exp),
            compute_saved=exp.compute_hours,
        )
        for exp in rows
    ]
    return SearchResponse(matches=matches, total=total, page=page, page_size=page_size)


@router.get("/similar/{experiment_id}", response_model=SearchResponse)
async def find_similar(
    experiment_id: str,
    db: DB,
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchResponse:
    results = await svc.find_similar(db, experiment_id, limit=limit)
    if not results and await svc.get_experiment(db, experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    matches = [
        SearchResult(
            experiment=ExperimentResponse.model_validate(exp),
            similarity=sim,
            compute_saved=exp.compute_hours,
        )
        for exp, sim in results
    ]
    return SearchResponse(matches=matches, total=len(matches), page=1, page_size=limit)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: DB) -> StatsResponse:
    data = await svc.get_stats(db)
    return StatsResponse(**data)
