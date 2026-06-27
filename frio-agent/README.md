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
frio creation preview                                    # Phase 3: UGC video brief (no spend)
frio creation render --approve                           # Phase 3: render MP4 (gated + spend caps)
frio creation carousel --slides 4                        # Phase 3: UGC image carousel brief
frio creation carousel --slides 4 --approve              # Phase 3: render carousel (gated)
frio optimize run --demo                                 # Phase 4: kill/scale proposals (synthetic data)
frio commerce publish --approve                          # Phase 5: publish listing (gated: needs seller approval)
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

### Phase 3 — AI-UGC creation: video + image carousels (this build)
`modules/creation.py` turns a demand-validated product + a mined hook into:
- a 30s **UGC video** brief → MP4 (`connectors/video_gen.py`), and
- a **UGC image carousel** brief → per-slide images (`connectors/image_ugc.py`).

Provider-agnostic and MCP-native by design. Primary plan: **Higgsfield** (one
official MCP server → Nano Banana Pro / Soul 2.0 images for carousels + Seedance/
Kling/Veo video + avatars + virality scoring); alternatives: Veo/Kling/Runway via
fal.ai, Arcads/Prizmad. (**Not** Sora — OpenAI discontinued it.)

Rendering is **gated**: `creation.render_video` / `creation.render_carousel` stay
disabled until `FRIO_CREATION_ENABLED=1`, require explicit human approval, and
every clip/image passes the per-clip / per-image + daily spend caps enforced
against the append-only `spend_ledger` (`frio/spend.py`). Previews are ungated and
spend nothing.

### Phase 4 — Optimize engine (this build)
`modules/optimize.py` is the deterministic money brain (no LLM, ever). `metrics.py`
aggregates `metrics_daily` into CTR/CPA/MER/CPC; `evaluate()` applies config-driven
thresholds to emit **kill / scale / hold** proposals recorded to the `decisions`
log. The safety invariant is enforced in code: **kills are spend-reducing (auto-
executable); scale-ups are spend-increasing (require human approval).** Thresholds
(`FRIO_OPT_*`) live in config, not code. Applying proposals to a live ad account
is Phase 6 — here it measures + proposes. `frio optimize run --demo` shows it on
synthetic data (2 kills, 1 scale-needs-approval, 1 hold).

### Phase 5 — Commerce / fulfillment (this build, GATED)
`modules/commerce.py` publishes listings and creates orders through the shared
`Fulfillment` interface — POD via **Printful**, Dropship via **CJ**
(`connectors/fulfillment.py`, selected by `make_fulfillment`). These are outward,
money-adjacent actions, so they stay **disabled until `FRIO_SELLER_APPROVED=1`**
and require explicit human approval every time; dropship publishing also refuses
non-compliant (retail-arbitrage) products. `sync_sales` pulls shop sales back into
`metrics_daily` so the optimize engine reads real results.

> **Offline mode:** every connector + the LLM degrade to deterministic fixtures when
> API keys are absent, so the pipeline runs end-to-end today (offline renders cost
> $0, listings get placeholder ids). Configure keys (`.env`, see `.env.example`) to
> swap in live data. Live API calls and the Prefect scheduling wrapper are the
> remaining follow-ups.

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
