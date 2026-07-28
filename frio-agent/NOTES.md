# Frío — deferred items / notes for later

## Deferred: FTC AI-UGC disclosure (revisit before going live)
Intentionally OFF for now (`FRIO_REQUIRE_AI_DISCLOSURE=0`, the default). The hooks
are already in place to switch it on later without new plumbing:
- `frio/compliance.py`: `has_ai_disclosure()` / `review_creative(requires_ai_disclosure=...)`.
- `frio/config.py`: `require_ai_disclosure`, `ai_disclosure_text`.
- `frio/modules/creation.py`: preview functions already call `review_creative`; just
  flip the flag and re-add the disclosure injection into the brief when ready.

Why it matters (research, May 2026): FTC requires a clear & conspicuous AI disclosure
on AI-generated UGC (3–5s / persistent for video), **up to $53,088 per violation**, and
the creator is independently liable. Turn this on before running live ads.

## Still active (NOT deferred)
- **Prohibited-claims scan** (`compliance.review`): flags TikTok-banned claims for the
  spirituality/wellbeing niche — disease/cure, weight/body transformation, before/after,
  wellness-cure, guaranteed-outcome/manifestation. Advisory; surfaced in `creation preview`.

## Future parallel workflow: AI design generation (deferred, guard-railed)
Designs currently come from the seller's OWN TikTok Shop catalog
(`connectors/tiktok_shop_catalog.py`). A second origin, `GeneratedDesignOrigin`
(`modules/product_pod.py`, stubbed → NotImplementedError), will generate NEW designs
to expand the test pool. Build it AFTER the existing-catalog loop yields real winners
(seed the generator with what actually sells). Hard requirements before enabling:
- **IP:** brief the model on ABSTRACTED winning themes/formats/aesthetics only —
  never feed competitor artwork to imitate; trademark/wordmark check on any text
  (spiritual/manifestation phrases are often trademarked); originality/similarity review.
- **Printability:** resolution/DPI, transparency, and safe-area gate before listing.
- **HITL:** human approval before any generated design is published.
Rationale: more design shots-on-goal raise the hit rate and our test→kill→scale loop
is built for it — but naive "generate from competitor designs" invites IP takedowns +
seller-score penalties and unprintable/low-converting "AI slop". Guardrails are mandatory.

## Seller eligibility — N/A
User already has an approved TikTok Shop, so the EIN / US-entity / bank verification
steps don't apply. (Ads Manager still needs a verified Business account + official
website to run paid ads — keep on the radar for Phase 6 go-live.)
