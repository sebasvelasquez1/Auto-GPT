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

You **create** the product (a design on a blank); a POD provider prints + ships
per order.

```
③ strategist ─► ④ POD PRODUCT ORIGIN  (modules/product_pod.py — BUILT)
                 ┌───────────────┬────────────────┬───────────────────┐
                 │ demand        │ AI design       │ product mockup     │
                 │ validate  ──► │ generate    ──► │ (Printful)         │ ─► demand-validated
                 │ (eRank;       │ (DALL·E/        │ (Nano Banana/      │    design + mockup
                 │  vol vs comp) │  Ideogram)      │  automated mockups)│
                 └───────────────┴────────────────┴───────────────────┘
                                         │
⑤ creation ─► ⑥ ads ─► ⑦ optimize  (shared)
                                         │ approved listing
                 ⑧ FULFILLMENT: PrintfulFulfillment (connectors/fulfillment.py — BUILT)
                    publish_product → listing ; auto-fulfill on sale ; sync_sales → metrics
```

- Margins ~10–30% (narrower) → stricter optimizer thresholds.
- Inherently policy-compliant (you make the product).

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
| **Product origin** | Design it: demand-validate → AI design → mockup | Source it: trend/ad-spy → pick winner → supplier SKU |
| **Demand signal** | Etsy/keyword search demand (eRank) | Is it *already* selling? (Kalodata/ad-spy) |
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
| ④ product origin | `modules/product_pod.py` (POD) · `make_product_origin()` · dropship = TODO |
| ⑤ creation | `modules/creation.py` · `connectors/{video_gen,image_ugc}.py` · `compliance.py` |
| ⑥ ads | `modules/ads.py` · `connectors/tiktok_ads.py` |
| ⑦ optimize | `modules/optimize.py` · `metrics.py` · `stats.py` (Wilson, Thompson) |
| ⑧ fulfillment | `connectors/fulfillment.py` (Printful / CJ) · `modules/commerce.py` |
| cross-cutting | `config.py` · `capabilities.py` · `spend.py` · `db/models.py` · `pipeline.py` |
```
