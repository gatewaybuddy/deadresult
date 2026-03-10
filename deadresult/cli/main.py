"""deadresult CLI — submit, search, and check experiments from the command line."""
from __future__ import annotations

import json
import sys

import click
import httpx
from rich.console import Console
from rich.table import Table

console = Console()
DEFAULT_URL = "http://localhost:8000"


def _client(base_url: str, api_key: str | None = None) -> httpx.Client:
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=30)


@click.group()
@click.option("--url", envvar="DEADRESULT_URL", default=DEFAULT_URL, help="API base URL")
@click.option("--api-key", envvar="DEADRESULT_API_KEY", default=None, help="API key")
@click.pass_context
def cli(ctx: click.Context, url: str, api_key: str | None) -> None:
    """DeadResult — searchable catalog of failed AI research experiments."""
    ctx.ensure_object(dict)
    ctx.obj["url"] = url
    ctx.obj["api_key"] = api_key


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def submit(ctx: click.Context, file: str) -> None:
    """Submit an experiment from a JSON file."""
    with open(file) as f:
        data = json.load(f)

    with _client(ctx.obj["url"], ctx.obj["api_key"]) as c:
        resp = c.post("/v1/experiments", json=data)

    if resp.status_code == 201:
        exp = resp.json()
        console.print(f"[green]Submitted:[/green] {exp['id']}")
    else:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        sys.exit(1)


@cli.command()
@click.option("-q", "--query", default=None, help="Free-text search query")
@click.option("--dataset", default=None, help="Filter by dataset name")
@click.option("--architecture", default=None, help="Filter by architecture")
@click.option("--status", default=None, help="Filter by status (failed, success, etc.)")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--limit", default=10, help="Max results")
@click.pass_context
def search(
    ctx: click.Context,
    query: str | None,
    dataset: str | None,
    architecture: str | None,
    status: str | None,
    tags: str | None,
    limit: int,
) -> None:
    """Search the experiment catalog."""
    params: dict[str, str | int | list[str]] = {"page_size": limit}
    if query:
        params["q"] = query
    if dataset:
        params["dataset"] = dataset
    if architecture:
        params["architecture"] = architecture
    if status:
        params["status"] = status
    if tags:
        params["tags"] = tags.split(",")

    with _client(ctx.obj["url"], ctx.obj["api_key"]) as c:
        resp = c.get("/v1/search", params=params)

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        sys.exit(1)

    data = resp.json()
    table = Table(title=f"Search Results ({data['total']} total)")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Dataset")
    table.add_column("Architecture")
    table.add_column("Hypothesis", max_width=50)

    for match in data["matches"]:
        exp = match["experiment"]
        status_style = "red" if exp["status"] == "failed" else "green"
        table.add_row(
            exp["id"],
            f"[{status_style}]{exp['status']}[/{status_style}]",
            exp["dataset_name"],
            exp.get("architecture") or "-",
            exp["hypothesis"][:50],
        )

    console.print(table)


@cli.command()
@click.argument("experiment_id")
@click.pass_context
def get(ctx: click.Context, experiment_id: str) -> None:
    """Get a single experiment by ID."""
    with _client(ctx.obj["url"], ctx.obj["api_key"]) as c:
        resp = c.get(f"/v1/experiments/{experiment_id}")

    if resp.status_code == 404:
        console.print(f"[red]Not found:[/red] {experiment_id}")
        sys.exit(1)
    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        sys.exit(1)

    console.print_json(resp.text)


@cli.command()
@click.option("-q", "--query", required=True, help="Hypothesis to check")
@click.option("--dataset", default=None, help="Dataset name")
@click.option("--architecture", default=None, help="Architecture type")
@click.option("--threshold", default=0.8, help="Similarity threshold to warn")
@click.pass_context
def check(
    ctx: click.Context,
    query: str,
    dataset: str | None,
    architecture: str | None,
    threshold: float,
) -> None:
    """Pre-experiment check: see if a similar experiment already exists."""
    params: dict[str, str | int] = {"q": query, "page_size": 5}
    if dataset:
        params["dataset"] = dataset
    if architecture:
        params["architecture"] = architecture

    with _client(ctx.obj["url"], ctx.obj["api_key"]) as c:
        resp = c.get("/v1/search", params=params)

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        sys.exit(1)

    data = resp.json()
    if data["total"] == 0:
        console.print("[green]PROCEED:[/green] No similar experiments found.")
        return

    has_warning = False
    for match in data["matches"]:
        exp = match["experiment"]
        sim = match.get("similarity")
        if exp["status"] == "failed":
            has_warning = True
            hours = match.get("compute_saved") or "?"
            console.print(
                f"[yellow]WARNING:[/yellow] Similar failed experiment {exp['id']} "
                f"(dataset={exp['dataset_name']}, arch={exp.get('architecture', '?')}). "
                f"Potential compute saved: {hours}h"
            )
            console.print(f"  Hypothesis: {exp['hypothesis'][:80]}")

    if not has_warning:
        console.print("[green]PROCEED:[/green] Similar experiments found but none failed.")


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show catalog statistics."""
    with _client(ctx.obj["url"], ctx.obj["api_key"]) as c:
        resp = c.get("/v1/stats")

    if resp.status_code != 200:
        console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        sys.exit(1)

    data = resp.json()
    console.print(f"[bold]Total experiments:[/bold] {data['total_experiments']}")
    console.print(f"[bold]Failed:[/bold] {data['total_failed']}")
    console.print(f"[bold]Successful:[/bold] {data['total_successful']}")
    console.print(f"[bold]Compute hours logged:[/bold] {data['total_compute_hours_logged']:.1f}")

    if data["top_datasets"]:
        console.print("\n[bold]Top Datasets:[/bold]")
        for ds in data["top_datasets"][:5]:
            console.print(f"  {ds['name']}: {ds['count']}")

    if data["top_architectures"]:
        console.print("\n[bold]Top Architectures:[/bold]")
        for a in data["top_architectures"][:5]:
            console.print(f"  {a['name']}: {a['count']}")


if __name__ == "__main__":
    cli()
