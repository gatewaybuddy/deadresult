"""Validation and serialization helpers for Lambda handlers.

Uses pydantic for input validation (same schemas as the FastAPI app).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Nested sub-schemas ---

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
    status: str
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


# --- API schemas ---

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


class ExportRequest(BaseModel):
    email: str = Field(..., min_length=5)
