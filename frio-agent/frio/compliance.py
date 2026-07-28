"""Ad-creative compliance pre-check (deterministic, advisory).

Protects the user from TikTok ad disapprovals + seller-score penalties and FTC
exposure, BEFORE money is spent rendering/launching. Encodes the researched
TikTok health/wellness bans (disease/cure, weight/body transformation, before/
after, wellness-"cure", guaranteed-outcome/manifestation) and the FTC AI-UGC
disclosure requirement (clear & conspicuous; up to $53,088 per violation).

Deterministic keyword/pattern scan — fast, no LLM, no false sense of legal
advice. It flags risk; a human still decides.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .capabilities import capability

# (category, severity, regex, note)
_RULES = [
    ("disease_cure", "high",
     r"\b(cure[sd]?|treat(s|ment)?|heal[s]?|prevent[s]?|reverse[s]?)\b.{0,30}"
     r"\b(disease|illness|condition|anxiety|depression|cancer|diabetes|insomnia)\b",
     "Disease treatment/cure claim — banned; immediate removal + seller penalty."),
    ("weight_body", "high",
     r"\b(lose weight|weight ?loss|fat ?burn|burn fat|slim down|melt fat|"
     r"muscle gain|body transformation)\b",
     "Weight/body-transformation claim — prohibited on TikTok ads."),
    ("before_after", "high",
     r"\bbefore\s*(?:&|and|/|-)\s*after\b",
     "Before/after transformation — prohibited."),
    ("wellness_cure", "high",
     r"\b(cure[s]?|fix(?:es)?|eliminate[s]?|reset[s]?)\b.{0,30}"
     r"\b(stress|fatigue|hormone|cortisol|testosterone)\b",
     "Wellness-cure claim — prohibited."),
    ("guaranteed_outcome", "medium",
     r"\b(guarantee[d]?|100%|instantly|overnight)\b.{0,40}"
     r"\b(results?|manifest|attract|abundance|money|wealth|rich)\b",
     "Guaranteed-outcome / manifestation claim — high disapproval risk."),
]
_COMPILED = [(c, sev, re.compile(rx, re.I), note) for c, sev, rx, note in _RULES]

_DISCLOSURE_HINTS = ("ai-generated", "ai generated", "created with ai", "ai actor",
                     "ai avatar", "#ad", "sponsored")


@dataclass
class Violation:
    category: str
    severity: str
    matched: str
    note: str


def check_claims(text: str) -> list[Violation]:
    text = text or ""
    found = []
    for cat, sev, rx, note in _COMPILED:
        m = rx.search(text)
        if m:
            found.append(Violation(cat, sev, m.group(0).strip(), note))
    return found


def has_ai_disclosure(text: str) -> bool:
    t = (text or "").lower()
    return any(h in t for h in _DISCLOSURE_HINTS)


def review_creative(text: str, *, requires_ai_disclosure: bool = True) -> dict:
    """Advisory compliance report for a piece of ad creative text."""
    violations = [asdict(v) for v in check_claims(text)]
    disclosure_present = has_ai_disclosure(text)
    needs_disclosure = requires_ai_disclosure and not disclosure_present
    return {
        "ok": not violations and not needs_disclosure,
        "violations": violations,
        "ai_disclosure_present": disclosure_present,
        "needs_ai_disclosure": needs_disclosure,
    }


@capability(
    "compliance.review",
    "Scan ad creative for prohibited claims + AI-UGC disclosure (advisory; no spend).",
    parameters={"text": {"type": "string", "required": True}},
    category="research",
)
def _cap_review(text: str, requires_ai_disclosure: bool = True) -> dict:
    return review_creative(text, requires_ai_disclosure=requires_ai_disclosure)
