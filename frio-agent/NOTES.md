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

## Seller eligibility — N/A
User already has an approved TikTok Shop, so the EIN / US-entity / bank verification
steps don't apply. (Ads Manager still needs a verified Business account + official
website to run paid ads — keep on the radar for Phase 6 go-live.)
