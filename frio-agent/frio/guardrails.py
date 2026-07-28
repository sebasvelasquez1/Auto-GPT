"""Account-safety guardrails — protect the seller account from the real ban vectors.

Research finding (2026-07-28, see knowledge/investigacion/): across Etsy, Redbubble and
Adobe Stock, accounts are not suspended for "using AI" as a category. They are suspended
for **volume + similarity + not-your-original-work**. Adobe Stock's stated trigger is
literally "a high volume of similar submissions" — even when every prompt was unique.

Documented suspensions are opaque: no reason given, appeals denied within the hour. An
autonomous loop must therefore NEVER be able to burn the seller's only account. These
are deterministic, code-enforced limits — not LLM judgment.

Also encodes Amazon's BSA Section 19 (announced 2026-02-17, effective 2026-03-04),
which requires automated agents to SELF-IDENTIFY as automated systems and, per
secondary sources, requires documented human authorization for bulk listing creation.
Our existing kills-auto/scales-gated asymmetry and human-attributed Decision audit trail
already satisfy the spirit of that rule; ``agent_user_agent`` makes the self-identification
explicit at the transport layer.

Evidence caveat: the policy claims above are search-extract tier (every primary page was
403-blocked this session) EXCEPT Etsy's own Transparency Reports, which were read and
which show 2024 was the purge year (+22% listing removals, 1.5x suspensions) and 2025
removals fell ~49% — contradicting the "escalating crackdown" narrative sold by
AI-compliance vendors. Re-verify before relaxing anything here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Terms that promise a MATERIAL PROPERTY the printed substrate does not have.
# Real-world failure documented by a POD operator: returns clustered on designs whose
# prompt contained "glowing" — buyers assumed UV-reactive fabric and returned when it
# wasn't. These are refund magnets, not policy violations.
_MATERIAL_CLAIM_TERMS = (
    "glow", "glowing", "glow-in-the-dark", "uv", "uv-reactive", "neon-lit",
    "metallic", "holographic", "iridescent", "reflective", "embossed", "embroidered",
    "foil", "shimmer", "sparkling", "3d", "textured",
)

# AI art tends to emit near-black (#0a0a0a etc.) which prints washed out on dark
# garments. Documented by the same operator. Absolute black is the fix.
_NEAR_BLACK = re.compile(r"#(0[0-9a-f]){3}\b", re.I)


@dataclass
class GuardrailVerdict:
    ok: bool
    reasons: list[str]

    def snapshot(self) -> dict:
        return {"ok": self.ok, "reasons": list(self.reasons)}


def check_listing_rate(recent_listing_times: list[datetime], *, max_per_day: int,
                       now: datetime | None = None) -> GuardrailVerdict:
    """Hard ceiling on autonomous listings per rolling 24h. Volume is the ban vector."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    recent = [t for t in recent_listing_times if t >= cutoff]
    if len(recent) >= max_per_day:
        return GuardrailVerdict(False, [
            f"Listing rate limit reached: {len(recent)} in the last 24h "
            f"(cap {max_per_day}). Bulk velocity is the documented suspension trigger."])
    return GuardrailVerdict(True, [])


def _shingles(text: str, n: int = 3) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def similarity(a: str, b: str) -> float:
    """Jaccard similarity over word-trigrams. Deterministic, no model needed."""
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 1.0 if sa == sb else 0.0
    return len(sa & sb) / len(sa | sb)


def check_design_differentiation(candidate: str, existing: list[str], *,
                                 max_similarity: float) -> GuardrailVerdict:
    """Reject near-duplicates. "High volume of SIMILAR submissions" is the stated
    trigger — uniqueness of the prompt is not enough, the OUTPUT must differ."""
    for other in existing:
        score = similarity(candidate, other)
        if score >= max_similarity:
            return GuardrailVerdict(False, [
                f"Too similar to an existing listing ({score:.0%} >= "
                f"{max_similarity:.0%}): {other[:60]!r}. Near-duplicates trip "
                f"mass-upload spam filters."])
    return GuardrailVerdict(True, [])


def check_material_claims(text: str) -> GuardrailVerdict:
    """Flag promises the substrate can't keep (refund magnets, not policy breaches)."""
    lowered = text.lower()
    hits = sorted({t for t in _MATERIAL_CLAIM_TERMS
                   if re.search(rf"\b{re.escape(t)}\b", lowered)})
    if hits:
        return GuardrailVerdict(False, [
            f"Implies a material property the print may not have: {', '.join(hits)}. "
            f"Documented return driver — buyers expect the physical effect."])
    return GuardrailVerdict(True, [])


def check_print_black(text: str) -> GuardrailVerdict:
    """Near-black prints washed out on dark garments; absolute #000000 is the fix."""
    found = _NEAR_BLACK.findall(text)
    if found and "#000000" not in text.lower():
        return GuardrailVerdict(False, [
            "Uses near-black instead of absolute #000000 — documented to print washed "
            "out on dark garments."])
    return GuardrailVerdict(True, [])


def agent_user_agent(version: str = "0.1") -> str:
    """Self-identify as an automated agent at the transport layer.

    Amazon BSA Section 19 requires automated agents to identify themselves as such.
    Doing this everywhere is both compliant and honest — and it is the opposite of the
    browser-automation/header-spoofing pattern that gets accounts banned.
    """
    return f"FrioAgent/{version} (automated commerce agent; contact=seller)"


def preflight_listing(title: str, existing_titles: list[str],
                      recent_listing_times: list[datetime], config,
                      now: datetime | None = None) -> GuardrailVerdict:
    """Run every guardrail before an autonomous listing action. All must pass."""
    reasons: list[str] = []
    for verdict in (
        check_listing_rate(recent_listing_times,
                           max_per_day=config.guard_max_listings_per_day, now=now),
        check_design_differentiation(title, existing_titles,
                                     max_similarity=config.guard_max_similarity),
        check_material_claims(title),
        check_print_black(title),
    ):
        if not verdict.ok:
            reasons.extend(verdict.reasons)
    return GuardrailVerdict(not reasons, reasons)
