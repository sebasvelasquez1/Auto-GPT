# Frío — architecture (two pipelines on one shared engine)

Frío runs the same loop for two business models. **One shared engine** does
research → strategy → creative → ads → optimize; the two pipelines diverge at only
**two swappable points**: where the product comes from (`ProductOrigin`) and how an
order is fulfilled (`Fulfillment`).

```
                       ┌──────────────────── SHARED ENGINE (built once) ────────────────────┐
  seed brand    ─────► │  ① competitor      ② ad research     ③ strategist                  │
  e.g. "Spiritual      │     discovery   ─►    (Creative      ─►  teardown + 30-day plan     │
  Gangster"            │     (audience          Center /          (hook/pattern/payoff,      │
                       │      overlap)           Meta Ad Lib)      kill rules, cadence)       │
                       └───────────────────────────────┬────────────────────────────────────┘
                                                        │  winning hooks + angles
        ╔═══════════════════ pipeline-specific ═════════▼════════════════════╗
        ║   ④ PRODUCT ORIGIN  ───────────────────────────────────────────►   ║
        ╚════════════════════════════════════════════════════════════════════╝
                                                        │  product + brief
                       ┌────────────────────────────────▼────────────────────────────────┐
  SHARED ENGINE (cont) │  ⑤ creation (gated $, HITL)     ⑥ ads (most gated, caps, HITL)   │
                       │     • UGC video                    • launch_campaign              │
                       │     • image carousel               • run_closed_loop              │
                       │     (Higgsfield: Nano Banana/      ⑦ optimize (kills auto,        │
                       │      Soul / Seedance/Kling/Veo)       scale-ups need approval)    │
                       └───────────────────┬─────────────────────────▲──────────────────--┘
                                           │ sells                    │ metrics
        ╔══════════════════ pipeline-specific ▼═════════════════════════════╗
        ║   ⑧ FULFILLMENT  ───────────►  sync_sales ──► metrics_daily ───────╝ (closes loop)
        ╚════════════════════════════════════════════════════════════════════╝
```

Compliance (TikTok-prohibited-claims scan) runs at creation; the closed loop feeds
ad/sales metrics back into optimize, which proposes kills (auto) and scale-ups
(human-approved) — and round it goes.

---

## Pipeline A — Print-on-Demand (POD)

The product is **the seller's OWN design** (already in their TikTok Shop; Shopify
later) printed on a blank. Designs are NOT generated and NOT taken from competitors
— competitor analysis only informs **which format (blank) to print on** (e.g. tank
top vs tee) and which themes are working.

```
③ strategist ─► ④ POD PRODUCT ORIGIN  (modules/product_pod.py — BUILT)
   + competitor    ┌──────────────────┬───────────────────┬─────────────────────┐
     format        │ pull YOUR designs │ recommend FORMATS │ pair design × top    │
     signal   ───► │ (TikTok Shop      │ from competitor   │ blank + mockup,      │ ─► test matrix:
                   │  catalog)         │ best-sellers      │ rank by theme demand │   your designs ×
                   │                   │ (tank>muscle>tee) │ (Printful mockup)    │   recommended blank
                   └──────────────────┴───────────────────┴─────────────────────┘
                                         │
⑤ creation ─► ⑥ ads ─► ⑦ optimize  (shared)
                                         │ approved listing
                 ⑧ FULFILLMENT: PrintfulFulfillment (connectors/fulfillment.py — BUILT)
                    publish_product → listing ; auto-fulfill on sale ; sync_sales → metrics
```

- Designs come from `connectors/tiktok_shop_catalog.py` (your catalog). Format
  recommendation = `recommend_blanks()` from competitor best-seller signal.
- Margins ~10–30% (narrower) → stricter optimizer thresholds.
- Inherently policy-compliant (you own the designs).

### POD roadmap
- **Phase 1 (now):** test the designs you ALREADY own on the competitor-top format.
- **Phase 2 (built, dormant):** `scale_winner_to_formats()` — take a WINNING design and
  scale it onto more competitor-recommended formats (tank → muscle tee → tee → …). Your
  own proven design, so zero IP risk. CLI: `frio product scale --design-id <id>`.
- **Phase 3 (deferred, guard-railed):** `GeneratedDesignOrigin` (stub) — generate NEW
  designs informed by *abstracted market themes* (never copying competitor artwork).
  Enable only after Phase 1–2 yield real winners to seed it, and only behind: IP
  guardrail (trademark/wordmark + originality review), printability gate (DPI/
  transparency/safe-area), and human approval. See `NOTES.md`.

---

## Pipeline B — Dropshipping

You **source** an existing winning product; an approved supplier ships it.

```
③ strategist ─► ④ DROPSHIP PRODUCT ORIGIN  (NOT BUILT YET — deferred "Phase 2A")
                 ┌───────────────┬────────────────┬───────────────────┐
                 │ trend/ad-spy  │ pick winning    │ approved-supplier  │
                 │ (Kalodata/    │ product (already│ SKU (CJ/Zendrop)   │ ─► compliant SKU
                 │  AutoDS/      │  selling)       │ + TikTok-Shop      │
                 │  Dropship.io) │                 │ compliance check   │
                 └───────────────┴────────────────┴───────────────────┘
                                         │   (make_product_origin('dropship')
                                         │    currently raises NotImplementedError)
⑤ creation ─► ⑥ ads ─► ⑦ optimize  (shared)
                                         │ approved listing
                 ⑧ FULFILLMENT: CJFulfillment (connectors/fulfillment.py — BUILT)
                    publish_product (REFUSES non-compliant / retail-arbitrage)
                    create_order → auto-buy from supplier ; sync_sales → metrics
```

- Margins ~15–40% (wider); broader product range (incl. non-printable).
- ⚠️ **Compliance enforced in code:** `CJFulfillment.publish_product` refuses
  non-compliant (retail-arbitrage) products — TikTok Shop bans reselling
  Amazon/AliExpress with their branding.

---

## Where they diverge (everything else is shared)

| Stage | POD (A) | Dropshipping (B) |
|---|---|---|
| **Product origin** | YOUR designs (TikTok Shop catalog) × competitor-recommended format (blank) | Source it: trend/ad-spy → pick winner → supplier SKU |
| **Demand signal** | Theme demand (eRank) on your designs + competitor format signal | Is it *already* selling? (Kalodata/ad-spy) |
| **Fulfillment** | Printful (print on demand) | CJ Dropshipping (auto-buy + ship) |
| **Compliance** | Inherently compliant | Must use approved supplier (enforced) |
| **Margins** | ~10–30% | ~15–40% |
| **Build status** | ✅ origin + fulfillment built (offline) | ⚠️ fulfillment built; **origin deferred (Phase 2A)** |

Selected by `config.pipeline` (`"pod"` | `"dropship"`) via `make_product_origin()`
and `make_fulfillment()`.

---

## Safety gates (both pipelines)

| Stage | Gate |
|---|---|
| competitor/research/strategist/optimize | ungated (no spend) |
| creation (video/carousel) | `creation_enabled` + human approval + per-clip/per-image + daily caps |
| commerce (publish/order) | `seller_approved` + human approval |
| ads (launch/scale) | `ads_live_enabled` + `seller_approved` + human approval + per-campaign + daily caps |
| optimize closed loop | kills auto-apply (reduce spend); scale-ups **never** auto-apply |

All caps are enforced in deterministic code against the append-only `spend_ledger`;
the LLM can never override them. Every gated action is written to the `decisions`
audit log.

---

## Code map

| Stage | Module / capability |
|---|---|
| ① discovery | `modules/competitors.py` · `connectors/{similarweb,sparktoro}.py` · `competitors.discover` |
| ② ad research | `connectors/ad_sources.py` (Creative Center, Meta Ad Library) |
| ③ strategist | `modules/strategist.py` · `strategist.teardown` / `strategist.plan` |
| ④ product origin | `modules/product_pod.py` (POD: existing catalog + `recommend_blanks`) · `connectors/tiktok_shop_catalog.py` · `GeneratedDesignOrigin` = future · dropship = TODO |
| ⑤ creation | `modules/creation.py` · `connectors/{video_gen,image_ugc}.py` · `compliance.py` |
| ⑥ ads | `modules/ads.py` · `connectors/tiktok_ads.py` |
| ⑦ optimize | `modules/optimize.py` · `metrics.py` · `stats.py` (Wilson, Thompson) — ad-level kill/scale |
| ⑦b analyzer | `modules/analyzer.py` · `financials.py` — product-level P&L (POAS/net profit) → cancel/watch/continue/scale |
| ⑧ fulfillment | `connectors/fulfillment.py` (Printful / CJ) · `modules/commerce.py` |
| cross-cutting | `config.py` · `capabilities.py` · `spend.py` · `db/models.py` · `pipeline.py` |
```
