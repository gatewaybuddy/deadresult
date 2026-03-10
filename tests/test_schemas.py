"""Tests for Pydantic schema validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from deadresult.schemas.experiment import ExperimentCreate


def test_valid_experiment_create() -> None:
    data = ExperimentCreate(
        hypothesis="Testing whether rotary embeddings improve perplexity on small datasets",
        approach={"model_architecture": "transformer", "modifications": ["rotary"]},
        dataset={"name": "TinyStories"},
        results={"status": "failed"},
    )
    assert data.hypothesis.startswith("Testing")
    assert data.approach.model_architecture == "transformer"
    assert data.results.status == "failed"
    assert data.tags == []


def test_experiment_create_missing_required() -> None:
    with pytest.raises(ValidationError):
        ExperimentCreate(
            hypothesis="Testing something important about model architecture",
            approach={"model_architecture": "transformer"},
            # missing dataset and results
        )


def test_experiment_create_hypothesis_too_short() -> None:
    with pytest.raises(ValidationError):
        ExperimentCreate(
            hypothesis="short",
            approach={"model_architecture": "mlp"},
            dataset={"name": "MNIST"},
            results={"status": "failed"},
        )


def test_experiment_create_full() -> None:
    data = ExperimentCreate(
        hypothesis="Full experiment with all fields populated for validation",
        approach={
            "model_architecture": "cnn",
            "modifications": ["batch_norm"],
            "training_approach": "sgd",
            "hyperparameters": {"lr": 0.01},
        },
        dataset={"name": "ImageNet", "size": "14M images", "preprocessing": "standard"},
        hardware={"gpu": "A100", "memory": "80GB", "compute_hours": 12.5},
        results={
            "status": "partial",
            "metrics": {"accuracy": 0.75},
        },
        submitter={"agent_id": "test", "verified": True, "reputation_score": 0.9},
        tags=["vision", "normalization"],
        notes="Partial improvement.",
        code_hash="sha256:def456",
        code_diff_url="https://github.com/example/repo/compare/base...exp",
    )
    assert data.hardware.compute_hours == 12.5
    assert data.submitter.verified is True
    assert len(data.tags) == 2
