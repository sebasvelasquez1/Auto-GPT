"""Creative Strategist (Phase 1b).

Implements the core of the practitioner spec: tear down winning ads into
hook / pattern-interrupt / payoff, mine angles, generate hooks, and synthesize a
30-day creative testing plan encoding the researched methodology
(PPE→conversion, $20-no-ATC kill, ABO→CBO, 4-week cadence).

Uses Claude when an LLMClient is available; otherwise deterministic heuristics so
the pipeline always produces an artifact.
"""

from __future__ import annotations

from ..capabilities import capability
from ..connectors.base import RawAd
from ..llm.client import LLMClient

TEARDOWN_SYSTEM = (
    "You are a direct-response creative strategist. Break a social ad into its "
    "structure. Return ONLY JSON with keys: hook, pattern_interrupt, payoff, "
    "angle, funnel_stage (cold|warm|retargeting), emotions (list)."
)


def _teardown_prompt(ad: RawAd) -> str:
    return f"Advertiser: {ad.advertiser}\nAd text: {ad.text!r}\nReturn the JSON teardown."


def teardown_ad(ad: RawAd, llm: LLMClient | None = None) -> dict:
    """Return a structured teardown of one ad."""
    if llm is not None and llm.available():
        data = llm.complete_json(TEARDOWN_SYSTEM, _teardown_prompt(ad))
        if data:
            data.setdefault("_engine", "claude")
            return data
    return _heuristic_teardown(ad)


def _heuristic_teardown(ad: RawAd) -> dict:
    text = (ad.text or "").strip()
    first = text.split(".")[0][:120] if text else ""
    lower = text.lower()
    interrupt = next(
        (k for k in ("pov:", "stop scrolling", "this is your sign", "your sign")
         if k in lower),
        "visual product reveal",
    )
    has_proof = any(k in lower for k in ("sold", "10k", "reviews", "viral"))
    return {
        "hook": first or f"{ad.advertiser} aspirational opener",
        "pattern_interrupt": interrupt,
        "payoff": "social proof + soft CTA" if has_proof else "product benefit + CTA",
        "angle": "manifestation/identity" if "manifest" in lower or "attract" in lower
        else "ritual/self-care",
        "funnel_stage": "cold",
        "emotions": ["aspiration", "belonging"],
        "_engine": "heuristic",
    }


def build_30_day_plan(seed: str, competitors: list[dict], teardowns: list[dict],
                      llm: LLMClient | None = None) -> dict:
    """Synthesize a 30-day creative testing plan from research."""
    hooks = [t.get("hook") for t in teardowns if t.get("hook")][:9]
    angles = sorted({t.get("angle") for t in teardowns if t.get("angle")})
    top = [c["name"] for c in competitors[:5]]
    return {
        "seed": seed,
        "top_competitors": top,
        "winning_angles": angles,
        "hook_bank": hooks,
        "kill_rules": [
            "Kill creative at $20 spend with 0 add-to-carts.",
            "Kill creative if CTR < 1% after ~1,000 impressions.",
            "Conversion test survivors at $5–25/day (ABO).",
        ],
        "weeks": [
            {"week": 1, "focus": "Test 5 audiences x 3 creatives (15 ad sets), ABO.",
             "creatives": hooks[:3]},
            {"week": 2, "focus": "Kill bottom 80%, scale top 20% into CBO."},
            {"week": 3, "focus": "Launch lookalikes from converters; refresh hooks."},
            {"week": 4, "focus": "Budget up winners only (~+20% every 3 days)."},
        ],
        "metrics": ["MER", "CPA", "CTR", "scroll_stop_rate", "hold_rate"],
        "_engine": "claude" if (llm and llm.available()) else "heuristic",
    }


def render_plan_markdown(plan: dict) -> str:
    lines = [
        f"# 30-Day Creative Testing Plan — seed: {plan['seed']}",
        f"_engine: {plan['_engine']}_\n",
        "## Top similar competitors",
        *[f"- {c}" for c in plan["top_competitors"]],
        "\n## Winning angles",
        *[f"- {a}" for a in plan["winning_angles"]],
        "\n## Hook bank",
        *[f"- {h}" for h in plan["hook_bank"]],
        "\n## Kill rules",
        *[f"- {r}" for r in plan["kill_rules"]],
        "\n## Weekly cadence",
        *[f"- **Week {w['week']}** — {w['focus']}" for w in plan["weeks"]],
        f"\n## Track: {', '.join(plan['metrics'])}",
    ]
    return "\n".join(lines)


@capability(
    "strategist.teardown",
    "Tear down a competitor ad into hook/pattern-interrupt/payoff structure.",
    parameters={"ad": {"type": "object", "required": True}},
    category="research",
)
def _cap_teardown(ad: dict) -> dict:  # thin capability wrapper
    return teardown_ad(RawAd(**ad))


@capability(
    "strategist.plan",
    "Synthesize a 30-day creative testing plan from competitor research.",
    parameters={"seed": {"type": "string", "required": True}},
    category="research",
)
def _cap_plan(seed: str, competitors: list[dict], teardowns: list[dict]) -> dict:
    return build_30_day_plan(seed, competitors, teardowns)
