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
research_app = typer.Typer(help="Ad research + strategist (Phase 1b)")
strategist_app = typer.Typer(help="Creative strategist (Phase 1b)")
product_app = typer.Typer(help="Product origin (Phase 2)")
db_app = typer.Typer(help="Database")
app.add_typer(capabilities_app, name="capabilities")
app.add_typer(competitors_app, name="competitors")
app.add_typer(research_app, name="research")
app.add_typer(strategist_app, name="strategist")
app.add_typer(product_app, name="product")
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


@research_app.command("run")
def research_run(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    competitors: int = typer.Option(5, help="Max competitors to research"),
    ads: int = typer.Option(5, help="Ads per competitor"),
    persist: bool = typer.Option(True, help="Persist to the database"),
) -> None:
    """Discover competitors, pull their ads, and tear each down."""
    from .pipeline import run_phase1

    res = run_phase1(seed=seed, limit_competitors=competitors,
                     ads_per_competitor=ads, persist=persist)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys / LLM) — using deterministic fixtures.\n")
    typer.echo(f"Seed: {res.seed}")
    typer.echo(f"Competitors: {len(res.competitors)} | Ads torn down: {len(res.ads)}")
    if res.ads:
        t = res.ads[0]["teardown"]
        typer.echo(f"Sample teardown ({t.get('_engine')}): "
                   f"hook={t.get('hook')!r} angle={t.get('angle')!r}")
    if res.persisted:
        typer.echo(f"Persisted: {res.persisted}")


@strategist_app.command("plan")
def strategist_plan(
    seed: str = typer.Option(None, help="Seed brand (defaults to config seed_brands)"),
    out: str = typer.Option(None, help="Write the plan markdown to this path"),
    persist: bool = typer.Option(True, help="Persist research to the database"),
) -> None:
    """Produce the 30-day creative testing plan (the Phase 1 deliverable)."""
    from .modules.strategist import render_plan_markdown
    from .pipeline import run_phase1

    res = run_phase1(seed=seed, persist=persist)
    md = render_plan_markdown(res.plan)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys / LLM) — using deterministic fixtures.\n")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(md)
        typer.echo(f"Wrote plan to {out}")
    else:
        typer.echo(md)


@product_app.command("discover")
def product_discover(
    niche: str = typer.Option(None, help="Niche (defaults to config niche)"),
    limit: int = typer.Option(20, help="Max products"),
    persist: bool = typer.Option(True, help="Persist to the database"),
) -> None:
    """Phase 2: demand-validate design ideas, then generate design + mockup."""
    from .pipeline import run_phase2

    res = run_phase2(niche=niche, limit=limit, persist=persist)
    if res.offline:
        typer.echo("⚠ OFFLINE mode (no API keys) — using deterministic fixtures.\n")
    typer.echo(f"Niche: {res.niche} | Pipeline: {res.pipeline}")
    typer.echo(f"Demand-validated products: {len(res.products)}\n")
    for p in res.products:
        d = p["metadata"]["demand"]
        typer.echo(f"  [{d['score']:.2f}] {p['title']}  "
                   f"(vol={d['search_volume']}, comp={d['competition']})")
        typer.echo(f"          design={p['metadata']['design_uri']}")
        typer.echo(f"          mockup={p['metadata']['mockup_uri']}")
    if res.persisted:
        typer.echo(f"\nPersisted: {res.persisted}")


@db_app.command("init")
def db_init() -> None:
    """Create all tables (dev/test convenience; Alembic owns prod migrations)."""
    from .db.base import init_db

    config = load_config()
    init_db(config.database_url)
    typer.echo(f"Initialized schema at {config.database_url}")


if __name__ == "__main__":
    app()
