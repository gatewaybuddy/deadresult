from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Nested sub-schemas matching the spec ---


class ApproachSchema(BaseModel):
    model_architecture: str
    modifications: list[str] = Field(default_factory=list)
    training_approach: str | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class DatasetSchema(BaseModel):
    name: str
    size: str | None = None
    preprocessing: str | None = None


class HardwareSchema(BaseModel):
    gpu: str | None = None
    memory: str | None = None
    compute_hours: float | None = None


class ResultsSchema(BaseModel):
    status: str  # "failed", "partial", "success", "inconclusive"
    final_perplexity: float | None = None
    baseline_perplexity: float | None = None
    convergence: str | None = None
    max_epochs_reached: bool | None = None
    memory_usage: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class SubmitterSchema(BaseModel):
    agent_id: str | None = None
    verified: bool = False
    reputation_score: float | None = None


# --- API request / response schemas ---


class ExperimentCreate(BaseModel):
    hypothesis: str = Field(..., min_length=10, max_length=2000)
    approach: ApproachSchema
    dataset: DatasetSchema
    hardware: HardwareSchema | None = None
    results: ResultsSchema
    submitter: SubmitterSchema | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = None
    code_hash: str | None = None
    code_diff_url: str | None = None


class ExperimentResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    hypothesis: str
    approach: dict[str, Any]
    dataset: dict[str, Any]
    hardware: dict[str, Any] | None
    results: dict[str, Any]
    submitter: dict[str, Any] | None
    status: str
    dataset_name: str
    architecture: str | None
    tags: list[str]
    notes: str | None
    code_hash: str | None
    code_diff_url: str | None
    compute_hours: float | None

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    items: list[ExperimentResponse]
    total: int
    page: int
    page_size: int


class SearchParams(BaseModel):
    q: str | None = None
    dataset: str | None = None
    architecture: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    experiment: ExperimentResponse
    similarity: float | None = None
    compute_saved: float | None = None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    matches: list[SearchResult]
    total: int
    page: int
    page_size: int


class FailureCategory(BaseModel):
    category: str
    count: int


class StatsResponse(BaseModel):
    total_experiments: int
    total_failed: int
    total_successful: int
    total_compute_hours_logged: float
    top_failure_categories: list[FailureCategory]
    top_datasets: list[dict[str, Any]]
    top_architectures: list[dict[str, Any]]
