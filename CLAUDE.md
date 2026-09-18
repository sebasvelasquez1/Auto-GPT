# Frío — project guidance for Claude

## My role (READ FIRST)

I am the **responsible technical owner / lead engineer** of the Frío agent system.
The user (project owner) is **not technically savvy** and is trusting me to run the
build. I act accordingly:

- **I own the technical decisions.** I choose the architecture, libraries, and
  approach, make the call when there's a sensible default, and only ask the user
  about things that are genuinely *their* business decision (budget, brand, going
  live with real money, legal/compliance trade-offs) — not technical minutiae.
- **I do the work end-to-end.** Write the code, run it, test it, verify it actually
  works, document it, commit, and push — every time. I never report something as
  done without having run it.
- **I protect the user from harm.** Money/commerce/ads capabilities stay gated and
  behind hard spend caps + human approval by default. I never put the system in a
  state that could spend real money or publish live without explicit sign-off.
- **I explain in plain language.** No unexplained jargon. When I use a technical
  term (PR, API key, branch…), I briefly say what it means.
- **I keep the user oriented.** After each chunk of work I summarize what changed,
  what works now, what's still stubbed, and the honest caveats — then offer the
  next step.
- **I take initiative responsibly.** If something is broken, risky, or a better path
  exists, I say so and act on it rather than waiting to be told.

In short: the user describes *what they want*; **I am responsible for making it real,
safely, and for keeping them informed.**

## Project

Frío is an autonomous TikTok-Shop commerce agent. Code lives in `frio-agent/`
(standalone package, built fresh — NOT on the legacy Auto-GPT in this repo).
Full plan: `/root/.claude/plans/objective-to-create-typed-nest.md`.

Pipeline: competitor discovery → ad research → creative strategist → AI-UGC
creation → test → optimize → ads. One shared engine, two pipelines (POD,
Dropshipping) behind `ProductOrigin`/`Fulfillment` interfaces.

## Core safety invariant

The LLM **proposes and explains**; deterministic code **measures and enforces**; a
human **authorizes spend**. Gated capabilities stay disabled until config flips
them on; every spend action checks hard caps + the append-only `spend_ledger`.
Actions that *reduce* spend (kills) may auto-run; actions that *increase* spend
require human sign-off.

## Regla de research (obligatoria — ver `frio-agent/knowledge/README.md`)

**No inventar. No presumir. No redondear hacia lo que suena bien.** Toda afirmación
de mercado/competidor/herramienta debe venir de una fuente citada; si el usuario
pega texto con cifras, se contrastan con búsqueda independiente y toda discrepancia
se documenta tal cual (no se elige la cifra que "suena mejor"). Distinguir siempre
si algo es una herramienta que un humano opera, o un agente que decide y ejecuta
solo — nunca se asume. El research puntual se marca como no-exhaustivo si no lo fue.
Hallazgos de mercado van a `frio-agent/knowledge/investigacion/`.

## Working conventions

- Develop on branch `claude/frio-shopping-agent-oxyduf`; commit + push after each
  working phase. Don't open a PR unless the user asks.
- Every connector degrades to deterministic **offline fixtures** when API keys are
  absent, so the pipeline always runs. Live API calls flip on via `.env` keys.
- Run `pytest` (in `frio-agent/`) before committing; keep it green.

## Status

- Phase 0 — skeleton ✅
- Phase 1 — competitor discovery + ad research + strategist ✅
- Phase 2 — POD product origin (demand → design → mockup) ✅
- Phase 3 — AI-UGC creation: video + image carousels (gated render + spend caps) ✅
  - Creation provider = Higgsfield via MCP (Nano Banana/Soul images + Seedance/Kling/Veo video).
- Phase 4 — Optimize engine (deterministic kill/scale rules; kills auto, scales need approval) ✅
- Phase 5 — Commerce/fulfillment (POD: Printful; Dropship: CJ) — GATED + HITL ✅
- Phase 6 — Ads + closed loop (TikTok Ads, spend caps + HITL) — GATED ✅

- Commercial/financial analyzer (product viability: true P&L, POAS, net profit →
  cancel/watch/continue/scale/**harvest**) ✅ — distinct from ad-level optimize.
- Fatigue/plateau layer ✅ — creative REFRESH on CTR-vs-own-baseline decay or high
  frequency; SCALE vetoed to HOLD on diminishing marginal returns (MER drop while
  spend rises); product plateau → HARVEST with seasonality guard (<12 weeks history).
- Predictive pre-score ✅ (Phase 3.5) — score hook/creative variants BEFORE the paid
  test (rule-based checklist or Claude judgment; gap identified from AdTest.AI-style
  commercial tools, see knowledge/investigacion/). Always ungated.
- Dashboard = private login web app (IntoSpirit); headline = per-product verdict
  (sirve/no sirve) with P&L. Deploy-ready for Render (DEPLOY.md). SaaS multi-tenant
  subscription = explicit ROADMAP, not built (fase inicial: IntoSpirit first).
- TikTok Ads MCP connection — discovery + dynamic client registration VERIFIED LIVE
  against TikTok (2026-09-16). No developer account or company needed: TikTok issued a
  real client_id to an unregistered public client. Two live-only bugs found and fixed
  (OAuth challenge is POST-only; metadata URL is the OIDC append form, not RFC 8414).
  Remaining step is HUMAN, not technical: the seller opens the approval link and pastes
  the returned address into `frio ads mcp-exchange --redirect-url='…'`. Details:
  knowledge/investigacion/2026-09-conexion-tiktok-shop-ads-consolidado.md §5.
- ⚠️ PRODUCT SELLABILITY vs AD EFFICIENCY ARE SEPARATE QUESTIONS — never conflate them.
  Organic sales are EVIDENCE the market wants the product (the cleanest evidence there
  is: nobody paid to show it to anyone), so they must never count against it; ads extend
  reach and scale what organic proved. An earlier version vetoed the product SCALE
  verdict on organic-inclusive revenue and was WRONG — corrected 2026-09-17 on the
  owner's challenge. `assess_viability` judges the product on total revenue;
  `ad_efficiency.assess_ad_efficiency` judges the ADS separately and is reported
  alongside, never as a gate. Its tiers: (1) paid-attributed revenue — Seller Center
  Data Compass "Ads Gross Revenue" vs "Non-Ads Gross Revenue", Shop-side only;
  (2) incremental lift over a pre-ad organic baseline; (3) explicit `unknown` — no
  optimistic default. Why Ads data can't answer it: TikTok attributes a purchase to a
  GMV Max campaign even when the buyer "doesn't view or click on any ads". NOTE: plain
  (non-GMV-Max) Shop Ads DO have real attribution (7-day click / 1-day view). See
  knowledge/investigacion/2026-09-medir-ads-tiktok-shop.md.
- 🤖 THE AUTONOMOUS RUNNER (`frio/agent.py`, `frio agent tick|run`) — added 2026-09-18
  after the owner pointed out that everything else was a capability and nothing woke up
  and used them. `decide()` reads the shop + verdicts + closed loop and classifies every
  action AUTO (spend-reducing/neutral: kills, verdicts, cost resolution — executed
  immediately) or APPROVAL (spend-increasing/outward: scale, launch, publish, paid
  render — QUEUED, never executed, and there is deliberately no flag that would execute
  one). So it can run unattended forever and the worst it can do alone is stop spending.
  The next-action choice is deterministic code, NOT an LLM — model judgement stays
  inside individual capabilities, never in the loop that touches money. One failing step
  is recorded and the tick continues, because an agent that dies on the first error
  silently stops running the business.
- AUTONOMY IS THE POINT — the agent derives product economics ITSELF; manual entry is
  only the fallback (corrected 2026-09-18 on the owner's challenge: an earlier design
  made typing costs in the primary path, which is backwards for an autonomous system).
  `cost_resolver.resolve_all` asks the SHOP what it sells (never a human-supplied list),
  takes price from the shop listing and product/shipping cost from the fulfilment
  provider, and records the SOURCE of every figure so a typed guess can never pass for
  live data (`fully_automatic()`). Manual `product_costs.json` fills only what no
  connector supplies. `MissingCostsError` is raised rather than defaulting a price —
  a fabricated price makes a fabricated verdict about real money. Platform fee
  default corrected 0.08 -> 0.06 (TikTok's own published US referral fee since
  2024-04-01); referral-fee sales tax (since 2025-11-01) and the refund admin fee (20%
  of referral, $5 cap) are real but state/return dependent, so `fin_referral_fee_tax_pct`
  stays a visible 0 to be filled from a real payout statement, not invented.
- ⚠️ ACCOUNT TOPOLOGY (user-declared 2026-09-16, see knowledge/CUENTAS-Y-JURISDICCION.md):
  TikTok Shop is US-only for this seller, whose personal TikTok is Colombian. So there
  are THREE separate identities — personal TikTok (Colombia, useless here), the US
  company's Shop/Seller Center, and the US company's Ads Manager. Authorizing with the
  personal account is THE mistake to avoid. An MCP grant covers every ad account that
  login can reach, so `FRIO_TIKTOK_ADS_ADVERTISER_ID` pins the one allowed account and
  `guardrails.require_pinned_ad_account` RAISES (never a soft verdict) on a mismatch or
  on any live action with no pin.
- PENDING from user: TikTok Shop developer credentials (promised; ask again after
  current tasks) → wires the real catalog + sales.

All 7 phases built end-to-end (offline-safe, 86 tests). Remaining work = finishing
each connector's LIVE API call (gating/caps/audit already done) + optional Prefect
scheduling wrapper + the Dropship product-origin (Phase 2A) sibling to POD.
