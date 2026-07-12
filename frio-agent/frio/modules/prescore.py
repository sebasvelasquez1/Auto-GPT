"""Predictive pre-score — score creative BEFORE spending on the paid test.

The gap identified from researched commercial tools (AdTest.AI-style): most of the
POD/dropship literature goes straight from "build a creative" to "spend $1-20 to get
real signal." A pre-launch filter catches weak creatives for free.

Honesty note (per the project's no-invent research rule): this is NOT a trained ML
model — we have no such model, and claiming one would violate that rule. It is:
  (a) a transparent, rule-based checklist grounded in the creative-testing research
      already gathered (on-image text + concise copy outperform; ~10-20s video is the
      completion-rate sweet spot; a clear hook/pattern-interrupt/payoff structure
      matters; compliance violations predict disapproval) — used when no LLM is
      available, or
  (b) a Claude judgment call (same available()-gated pattern as strategist.teardown_ad)
      when an LLM is configured — more capable than a checklist, and legitimate here
      because NO MONEY is at stake yet.
  (c) an optional third-party scorer (e.g. AdTest.AI) — connector shape only; NOT a
      live integration (no account/API access), consistent with every other
      not-yet-wired connector in this codebase.

Never gated (no money involved) — purely advisory, always ungated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..capabilities import capability
from ..compliance import review_creative
from ..config import Config, load_config
from ..llm.client import LLMClient, make_llm

PRESCORE_SYSTEM = (
    "You are a senior direct-response creative judge. Score a UGC ad brief BEFORE any "
    "money is spent testing it. Judge only from the brief text (no video exists yet). "
    "Return ONLY JSON: {score (0-100), dimensions: {hook_clarity, pattern_interrupt, "
    "payoff_clarity, format_fit} each 0-100, reasons: [short strings]}."
)


@dataclass
class PreScore:
    score: float  # 0..100
    dimensions: dict
    reasons: list[str]
    recommendation: str  # "test" | "revise"
    engine: str  # heuristic | claude | adtest


def _heuristic_score(brief: dict) -> PreScore:
    """Transparent checklist — every point is traceable to a specific rule."""
    reasons: list[str] = []
    dims = {"hook_clarity": 50.0, "pattern_interrupt": 50.0,
           "payoff_clarity": 50.0, "format_fit": 50.0}

    hook = (brief.get("hook") or "").strip()
    if 8 <= len(hook) <= 70:
        dims["hook_clarity"] += 20
        reasons.append("Hook length in the concise-copy sweet spot (8-70 chars).")
    elif hook:
        dims["hook_clarity"] -= 10
        reasons.append("Hook is too short or too long — concise copy tests better.")
    else:
        dims["hook_clarity"] -= 30
        reasons.append("No hook found.")

    if brief.get("angle") and brief["angle"] not in ("", None):
        dims["pattern_interrupt"] += 15
        reasons.append("Has a distinct angle (not generic).")

    slides = brief.get("slides")
    if slides:  # carousel: hero-hook first slide + CTA-shaped last slide
        if len(slides) >= 2:
            dims["payoff_clarity"] += 15
            reasons.append("Carousel has a closing slide for the payoff/CTA.")
        dims["format_fit"] += 10
    else:  # video
        prompt = brief.get("video_prompt") or ""
        if "cta" in prompt.lower() or "shop" in prompt.lower() or "tap" in prompt.lower():
            dims["payoff_clarity"] += 15
            reasons.append("Video prompt includes a clear CTA.")
        # Research: ~10-20s is the completion-rate sweet spot for short-form video.
        if "30s" in prompt or "30 s" in prompt:
            dims["format_fit"] -= 10
            reasons.append("30s runs long vs the ~10-20s completion-rate sweet spot "
                          "for cold-audience video — consider trimming.")

    compliance = review_creative(f"{hook} {brief.get('video_prompt', '')} "
                                 f"{' '.join(s.get('caption', '') for s in (slides or []))}",
                                 requires_ai_disclosure=False)
    if not compliance["ok"]:
        dims["payoff_clarity"] -= 30
        for v in compliance["violations"]:
            reasons.append(f"Compliance risk ({v['category']}): {v['note']}")

    dims = {k: max(0.0, min(100.0, v)) for k, v in dims.items()}
    score = round(sum(dims.values()) / len(dims), 1)
    return PreScore(score=score, dimensions=dims, reasons=reasons,
                    recommendation="test" if score >= 60 else "revise",
                    engine="heuristic")


def _claude_score(brief: dict, llm: LLMClient) -> PreScore | None:
    prompt = f"Brief: {brief}\nScore it now."
    data = llm.complete_json(PRESCORE_SYSTEM, prompt)
    if not data or "score" not in data:
        return None
    return PreScore(score=float(data["score"]), dimensions=data.get("dimensions", {}),
                    reasons=data.get("reasons", []),
                    recommendation="test" if data["score"] >= 60 else "revise",
                    engine="claude")


def score_brief(brief: dict, config: Config | None = None,
                llm: LLMClient | None = None) -> PreScore:
    """Score one brief. Claude when available (more capable, no money at stake yet
    so an LLM judge is appropriate here); deterministic checklist otherwise."""
    config = config or load_config()
    if llm is not None and llm.available():
        result = _claude_score(brief, llm)
        if result is not None:
            result.recommendation = ("test" if result.score >= config.prescore_min_to_test
                                     else "revise")
            return result
    result = _heuristic_score(brief)
    result.recommendation = "test" if result.score >= config.prescore_min_to_test else "revise"
    return result


def rank_variants(briefs: list[dict], config: Config | None = None,
                  llm: LLMClient | None = None) -> list[dict]:
    """Score every candidate brief and return them ranked best-first.

    Implements the researched 4-stage flow's filter step: generate several
    variants, score them, recommend which to actually spend the test budget on.
    """
    config = config or load_config()
    scored = [{"brief": b, "prescore": asdict(score_brief(b, config, llm))} for b in briefs]
    scored.sort(key=lambda r: r["prescore"]["score"], reverse=True)
    return scored


class AdTestAIScorer:
    """Third-party scorer connector shape — NOT a live integration.

    We do not have an AdTest.AI account/API access; this mirrors every other
    not-yet-wired connector in this codebase (offline until a key is configured,
    then the real call still needs to be written and verified against the real API).
    """

    name = "adtest_ai"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.adtest_api_key)

    def score(self, brief: dict) -> PreScore:
        if not self.available():
            raise RuntimeError("AdTest.AI not configured (set FRIO_ADTEST_API_KEY).")
        raise NotImplementedError("wire the real AdTest.AI API call here")


@capability(
    "prescore.rank_variants",
    "Score hook/creative variants BEFORE spending on the paid test (advisory; no spend).",
    parameters={"briefs": {"type": "array", "required": True}},
    category="research",
)
def _cap_rank(briefs: list[dict], config: Config | None = None) -> list[dict]:
    config = config or load_config()
    return rank_variants(briefs, config, make_llm(config))
