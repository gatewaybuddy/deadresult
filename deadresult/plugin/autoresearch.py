"""DeadResult autoresearch plugin.

Hooks into autoresearch's experiment flow to:
1. Auto-submit results after each experiment completes.
2. Pre-check the catalog before starting to avoid duplicating dead ends.

Usage:
    from deadresult.plugin import DeadResultPlugin

    plugin = DeadResultPlugin(base_url="https://deadresult.agentpier.org")

    # Pre-check
    check = await plugin.check_before_experiment(hypothesis=..., approach=..., dataset=...)
    if check.should_skip:
        print(f"Skipping — similar experiment already failed. Saved ~{check.compute_saved}h")

    # Auto-submit
    await plugin.submit_result(experiment_data)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class PreCheckResult:
    should_skip: bool
    reason: str | None = None
    similar_id: str | None = None
    similarity: float = 0.0
    compute_saved: float | None = None


class DeadResultPlugin:
    """Client plugin for autoresearch integration."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        similarity_threshold: float = 0.8,
        auto_submit: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.similarity_threshold = similarity_threshold
        self.auto_submit = auto_submit
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30)

    async def check_before_experiment(
        self,
        hypothesis: str,
        approach: dict[str, Any] | None = None,
        dataset: str | None = None,
    ) -> PreCheckResult:
        """Query catalog to see if a similar experiment was already tried."""
        params: dict[str, Any] = {"q": hypothesis}
        if dataset:
            params["dataset"] = dataset
        if approach and "model_architecture" in approach:
            params["architecture"] = approach["model_architecture"]

        resp = await self._client.get("/v1/search", params=params)
        if resp.status_code != 200:
            return PreCheckResult(should_skip=False, reason="Catalog unreachable")

        data = resp.json()
        for match in data.get("matches", []):
            sim = match.get("similarity")
            exp = match.get("experiment", {})
            status = exp.get("status", "")
            if sim is not None and sim >= self.similarity_threshold and status == "failed":
                return PreCheckResult(
                    should_skip=True,
                    reason=f"Similar experiment {exp.get('id')} failed (similarity={sim:.2f})",
                    similar_id=exp.get("id"),
                    similarity=sim,
                    compute_saved=match.get("compute_saved"),
                )

        return PreCheckResult(should_skip=False)

    async def submit_result(self, experiment_data: dict[str, Any]) -> dict[str, Any] | None:
        """Submit an experiment result to the catalog."""
        resp = await self._client.post("/v1/experiments", json=experiment_data)
        if resp.status_code == 201:
            return resp.json()
        return None

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> DeadResultPlugin:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
