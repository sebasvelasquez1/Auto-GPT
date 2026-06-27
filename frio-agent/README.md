# Frío — autonomous TikTok-Shop commerce agent

A standalone, Claude-centric, MCP-friendly engine for running the niche
commerce loop: **competitor discovery → ad research → creative strategist →
AI-UGC creation → test → optimize → ads**. One shared engine serves **two
pipelines** behind common `ProductOrigin` / `Fulfillment` interfaces:

- **POD** (print-on-demand): design the product; Printful/Printify/Gelato prints + ships.
- **Dropshipping**: source pre-made winning products; supplier (CJ/Zendrop) ships.

> Built standalone (not on the legacy Auto-GPT in this repo). It borrows two
> patterns from it: the `@command`-style capability registry with `enabled` /
> `disabled_reason` gating, and the retry/backoff connector pattern.

## Core safety invariant

The LLM **proposes and explains**; deterministic code **measures and enforces**;
a human **authorizes spend**. Gated capabilities (live ads, commerce, paid video
render) stay disabled until config flips them on, and every spend action is
checked against hard caps + the append-only `spend_ledger`. Actions that *reduce*
spend (kills) can auto-run; actions that *increase* spend require human sign-off.

## Running it

```bash
cd frio-agent
pip install -e .            # core deps: pydantic, pydantic-settings, sqlalchemy, typer

frio capabilities list                                   # gated tools shown disabled + why
frio competitors discover --seed "Spiritual Gangster"    # Phase 1a discovery
frio research run --seed "Spiritual Gangster"            # discover -> fetch ads -> teardown
frio strategist plan --seed "Spiritual Gangster"         # the 30-day testing plan (deliverable)
frio product discover --niche spirituality               # Phase 2 POD: demand -> design -> mockup
frio db init                                             # create tables (dev/test)
pip install -e '.[dev]' && pytest                        # tests
```

### Phase 0 — skeleton
Config + gated capability registry, schema, pipeline interfaces, CLI.

### Phase 1 — competitor discovery + ad research + strategist (this build)
- **1a discovery** (`modules/competitors.py`): seeds from a brand (e.g. Spiritual
  Gangster), expands by audience overlap across providers (Similarweb web-traffic +
  SparkToro social), scores client similarity, tags direct/indirect/aspirational.
- **ad research** (`connectors/ad_sources.py`): pulls competitor ads from TikTok
  Creative Center + Meta Ad Library.
- **1b strategist** (`modules/strategist.py`): Claude tears each ad into
  hook/pattern-interrupt/payoff and synthesizes the **30-day creative testing plan**
  (kill rules + 4-week cadence). Falls back to deterministic heuristics with no key.

### Phase 2 — POD product origin (this build)
`modules/product_pod.py` implements the `ProductOrigin` interface for POD:
validate search demand (`connectors/demand.py`, eRank-style) → keep ideas above
`FRIO_DEMAND_THRESHOLD` → generate a design (`connectors/design_gen.py`) and a
product mockup (`connectors/mockups.py`, Printful) for each survivor. Ranks by a
blended demand-vs-competition score so low-competition ideas beat saturated ones.
The Dropshipping product origin plugs into the same `make_product_origin` factory
in a later phase.

> **Offline mode:** every connector + the LLM degrade to deterministic fixtures when
> API keys are absent, so the pipeline runs end-to-end today. Configure keys
> (`.env`, see `.env.example`) to swap in live data. Live API calls and the Prefect
> scheduling wrapper are the remaining follow-ups.

## Layout

```
frio/
  config.py         pydantic-settings Config + gating flags + spend caps
  capabilities.py   @capability decorator + registry (enabled / disabled_reason)
  interfaces.py     ProductOrigin / Fulfillment (swappable per pipeline)
  connectors/       external-API connector boundary (retry/backoff helper)
  db/               SQLAlchemy models incl. competitors, decisions, spend_ledger
  modules/          capability modules (competitors discovery; gated ads example)
  cli.py            typer CLI
```

See `/root/.claude/plans/objective-to-create-typed-nest.md` for the full plan
(architecture, two pipelines, phased build order, risks, HITL/spend gates).
