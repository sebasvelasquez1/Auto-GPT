"""Frío CLI (typer).

Phase 0 demoable surface:
  frio capabilities list                       # gated tools shown disabled + why
  frio competitors discover --seed "Spiritual Gangster"
  frio db init                                 # create tables (dev/test)
"""

from __future__ import annotations

import json

import typer

from .capabilities import REGISTRY, load_all_capabilities
from .config import load_config

app = typer.Typer(add_completion=False, help="Frío autonomous commerce agent")
capabilities_app = typer.Typer(help="Inspect capabilities")
competitors_app = typer.Typer(help="Competitor discovery (Phase 1a)")
db_app = typer.Typer(help="Database")
app.add_typer(capabilities_app, name="capabilities")
app.add_typer(competitors_app, name="competitors")
app.add_typer(db_app, name="db")


@capabilities_app.command("list")
def capabilities_list() -> None:
    """List all capabilities and whether they are enabled under current config."""
    load_all_capabilities()
    config = load_config()
    for cap in REGISTRY.all():
        on = cap.is_enabled(config)
        status = "ENABLED " if on else "disabled"
        line = f"  [{status}] {cap.name:24s} ({cap.category})  {cap.description}"
        typer.echo(line)
        if not on and cap.disabled_reason:
            typer.echo(f"             ↳ {cap.disabled_reason}")


@competitors_app.command("discover")
def competitors_discover(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    limit: int = typer.Option(20, help="Max competitors"),
) -> None:
    """Discover competitors who share our customers, ranked by similarity."""
    load_all_capabilities()
    config = load_config()
    seed = seed or config.seed_brands
    discover = REGISTRY.get("competitors.discover").func
    results = discover(seed=seed, limit=limit)
    typer.echo(f"Seed: {seed}")
    for c in results:
        typer.echo(
            f"  {c['similarity_score']:.2f}  {c['relation']:12s}  {c['name']}"
            + (f"  ({c['website']})" if c.get("website") else "")
        )
    typer.echo(json.dumps(results, indent=2))


@db_app.command("init")
def db_init() -> None:
    """Create all tables (dev/test convenience; Alembic owns prod migrations)."""
    from .db.base import init_db

    config = load_config()
    init_db(config.database_url)
    typer.echo(f"Initialized schema at {config.database_url}")


if __name__ == "__main__":
    app()
