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
frio optimize run --demo                                 # Phase 4: ad-level kill/scale proposals
frio analyzer product --price 30 --cost 9 --fulfillment 5 --units 40 --ad-spend 120  # product P&L + verdict
frio commerce publish --approve                          # Phase 5: publish listing (gated: needs seller approval)
frio ads launch --budget 5 --approve                     # Phase 6: launch campaign (gated + spend caps)
frio ads loop --demo                                     # Phase 6: closed loop (auto-kill, surface scales)
frio db init                                             # create tables (dev/test)
pip install -e '.[dev]' && pytest                        # tests

# Local dashboard (read-only, password-protected):
pip install -e '.[dashboard]'
export FRIO_DASHBOARD_PASSWORD='your-secret'
frio dashboard                                           # http://127.0.0.1:8787 (local only)
```

### Dashboard (private, login-protected) — IntoSpirit
The **headline of the dashboard is the business answer**: for every priced product,
*sirve o no sirve* (cancel / watch / continue / scale), backed by its real P&L (net
profit, POAS, margin) — computed by the financial analyzer, not just raw tables. Below
that sits the technical detail: products catalog, ad-level optimizer verdicts, the
spend ledger, and the decisions audit log.

```
frio demo-seed          # one command: research + products + pricing + sales -> verdicts
frio analyzer summary   # the same verdicts in the terminal
frio dashboard          # the same verdicts as the dashboard's headline section
```

To make it show YOUR real numbers: run the pipeline (`research run`, `product
discover`), price each product (`frio product set-price --title "..." --price --cost
--fulfillment`), and sync its real sales + ad spend (`commerce.sync_sales(...,
ad_spend=...)`, gated to your approved shop) — the verdict updates automatically.

`frio/dashboard.py` is a FastAPI web app with a **real session login** (signed cookie)
— confidential by default: every data route requires an authenticated session, and
unauthenticated visitors only see the login page. It is **read-only** — no endpoint
spends money or launches/publishes; those stay behind their CLI gates + caps.

Runs as a real server (Render + Postgres, HTTPS) or locally. Requires
`FRIO_DASHBOARD_PASSWORD` + `FRIO_DASHBOARD_SESSION_SECRET`. Deploy: see `DEPLOY.md`.

> **Roadmap — sellable, multi-tenant SaaS.** POD + dropshipping testing is a huge
> market; this could eventually be sold by subscription to other sellers. The current
> build is intentionally the **single-tenant IntoSpirit version first** — prove the
> pipeline + dashboard deliver real value for one business before generalizing. The
> auth layer is structured so it can grow into per-client logins (each client sees only
> their own data) later without reworking the render/data layers.

> The static `export-site` / Netlify path also exists, but it produces a *public*
> snapshot — not suitable for confidential data. Use the Render login app for IntoSpirit.

**How the dashboard connects to the agent — the shared database.** There is no
extra wiring: the agent (pipeline + modules) WRITES results to the DB (`products`,
`competitors`, `decisions`, `spend_ledger`, `metrics_daily`), and the dashboard READS
the same DB via the same SQLAlchemy models. Point both at the same `FRIO_DATABASE_URL`
and they're connected — the dashboard reflects whatever the agent has done.

```
   agent (CLI / pipeline / modules)                 dashboard (FastAPI, read-only)
   research / product / optimize / ads / commerce        frio dashboard
                 │  writes                                      ▲  reads
                 ▼                                              │
            ┌───────────────────── FRIO_DATABASE_URL ─────────────────────┐
            │  products · competitors · decisions · spend_ledger · metrics │
            └──────────────────────────────────────────────────────────────┘
```
Live verification: run `frio research run` / `frio product discover` /
`frio optimize run --demo`, then open `frio dashboard` on the same DB — your designs,
verdicts and audit log appear.

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
`modules/product_pod.py` implements the `ProductOrigin` interface for POD using the
seller's OWN designs: pull existing designs from the TikTok Shop catalog
(`connectors/tiktok_shop_catalog.py`) → recommend the format/blank from competitor
best-sellers (`recommend_blanks`, e.g. tank top > tee) → pair each design with the
top format + a Printful mockup (`connectors/mockups.py`), ranked by theme demand
(`connectors/demand.py`, eRank-style). `scale_winner_to_formats` (Phase 2 roadmap)
multiplies a winning design onto more formats. AI design generation is deferred
(`GeneratedDesignOrigin`, Phase 3 — see `NOTES.md`). The Dropshipping product origin
plugs into the same `make_product_origin` factory in a later phase.

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

### Fatigue, plateau & harvest (full lifecycle, not just kill/scale)
The engine now covers the *whole* life of a winner, not just its birth:
- **REFRESH (creative fatigue)** — `optimize.detect_fatigue`: recent CTR ≥20% below
  its own baseline, or frequency >3.5 → the ad is wearing out (TikTok fatigues ~4×
  faster than Meta). Proposal only — replacing creative costs money.
- **Stop-scaling (plateau)** — `optimize.detect_scaling_plateau`: spend up ≥20% while
  MER falls ≥15% = diminishing *marginal* returns → SCALE proposals are vetoed into
  HOLD ("keep the last efficient budget; scale horizontally").
- **HARVEST (product lifecycle)** — `analyzer.lifecycle_stage`: units falling ≥3
  straight weeks while still net-profitable → 🌾 harvest verdict (stop scaling, milk
  remaining demand, prep the replacement). Maturity ≠ decline: profitable plateaus are
  harvested, never killed. With <12 weeks of history the verdict flags
  **"verify it isn't seasonality"** before any cancel.

### Phase 4 — Optimize engine (this build)
`modules/optimize.py` is the deterministic money brain (no LLM, ever). `metrics.py`
aggregates `metrics_daily` into CTR/CPA/MER/CPC; `evaluate()` applies config-driven
thresholds to emit **kill / scale / hold** proposals recorded to the `decisions`
log. The safety invariant is enforced in code: **kills are spend-reducing (auto-
executable); scale-ups are spend-increasing (require human approval).** Thresholds
(`FRIO_OPT_*`) live in config, not code. Applying proposals to a live ad account
is Phase 6 — here it measures + proposes. `frio optimize run --demo` shows it on
synthetic data (2 kills, 1 scale-needs-approval, 1 hold).

### Commercial / financial analyzer (product viability)
`financials.py` + `modules/analyzer.py` compute a product's TRUE unit economics —
revenue, COGS, fulfillment, platform fees (TikTok Shop apparel ≈ 8%), returns AND ad
spend → contribution per unit, **net profit, POAS, break-even ROAS** — and emit a
business-level verdict: **cancel / watch / continue / scale**. This is distinct from
the ad-level kill in `optimize.py`: optimize cuts bad *creatives*; the analyzer
decides whether the *product itself* is worth selling (e.g. cancel if you lose money
on every unit, or if it's a net loss after a fair test). Deterministic; no LLM in the
money math. CLI: `frio analyzer product …`; capability `analyzer.product_viability`.

### Phase 5 — Commerce / fulfillment (this build, GATED)
`modules/commerce.py` publishes listings and creates orders through the shared
`Fulfillment` interface — POD via **Printful**, Dropship via **CJ**
(`connectors/fulfillment.py`, selected by `make_fulfillment`). These are outward,
money-adjacent actions, so they stay **disabled until `FRIO_SELLER_APPROVED=1`**
and require explicit human approval every time; dropship publishing also refuses
non-compliant (retail-arbitrage) products. `sync_sales` pulls shop sales back into
`metrics_daily` so the optimize engine reads real results.

### Phase 6 — Live ads + closed loop (this build, MOST GATED)
`modules/ads.py` launches/scales TikTok campaigns (`connectors/tiktok_ads.py`) and
runs the closed loop. Launch + scale stay disabled until `FRIO_ADS_LIVE_ENABLED=1`
**and** `FRIO_SELLER_APPROVED=1`, require explicit approval, and every committed
dollar passes the per-campaign + daily caps on the `spend_ledger` (hard stop). The
closed loop reads metrics → optimize proposals and applies them asymmetrically:
**kills auto-apply (cut spend); scale-ups are only ever surfaced for human approval.**

> **Offline mode:** every connector + the LLM degrade to deterministic fixtures when
> API keys are absent, so the whole loop runs end-to-end today (offline renders cost
> $0, listings/campaigns get placeholder ids). Configure keys (`.env`, see
> `.env.example`) to swap in live data; the remaining follow-up is finishing each
> connector's live API call (the gating, caps, and audit logging are done) plus an
> optional Prefect scheduling wrapper.

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
