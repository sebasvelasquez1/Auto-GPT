"""The autonomous runner — the thing that makes this an AGENT and not a toolbox.

Everything else in this package is a CAPABILITY: research competitors, price a product,
judge whether it sells, kill a losing ad. Real, tested, and all of it inert until
somebody types a command. This module is what wakes up, looks at the state of the
business, decides what needs doing, and does it.

Built 2026-09-18 after the owner pointed out the gap: "DEBE HABER un agente o varios que
hagan estas labores." He was right — there wasn't one.

HOW IT DECIDES (deterministic, by design)
The decision of WHAT to do next is ordinary code, not a language model. The project's
safety invariant is that the LLM proposes and explains, deterministic code measures and
enforces, and a human authorises spend; an LLM choosing the agent's next action would
put model judgement in the money path. The LLM's place is inside individual capabilities
(writing a creative brief, tearing down a competitor ad), never in this loop.

THE ASYMMETRY THAT KEEPS IT SAFE
Each decided action is classified:
  - AUTO      — reduces or does not change spend (kill a loser, refresh research,
                recompute a verdict). Executed immediately, no human needed.
  - APPROVAL  — increases spend or acts outwardly (scale a winner, launch a campaign,
                publish a listing, render paid creative). NEVER executed here. It is
                queued with its reasoning for a human to approve.
So the agent can run unattended forever and the worst it can do on its own is stop
spending money. Every path that starts spending stops at a person.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .config import Config, load_config

AUTO = "auto"
APPROVAL = "needs_approval"
BLOCKED = "blocked"


@dataclass
class Action:
    """One thing the agent decided to do, and why."""

    name: str
    mode: str                      # auto | needs_approval | blocked
    reason: str
    detail: dict = field(default_factory=dict)
    result: str | None = None      # filled in after execution

    def snapshot(self) -> dict:
        return asdict(self)


@dataclass
class TickReport:
    """What the agent did on one wake-up. This is the audit trail."""

    at: str
    actions: list[Action] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def executed(self) -> list[Action]:
        return [a for a in self.actions if a.mode == AUTO]

    def awaiting_human(self) -> list[Action]:
        return [a for a in self.actions if a.mode == APPROVAL]

    def blocked(self) -> list[Action]:
        return [a for a in self.actions if a.mode == BLOCKED]

    def snapshot(self) -> dict:
        return {"at": self.at, "actions": [a.snapshot() for a in self.actions],
                "errors": list(self.errors),
                "counts": {"executed": len(self.executed()),
                           "awaiting_human": len(self.awaiting_human()),
                           "blocked": len(self.blocked())}}


def _safe(report: TickReport, label: str, fn):
    """One failing step must never stop the whole tick — an agent that dies on the
    first error is an agent that silently stops managing the business."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - deliberately broad; recorded, not raised
        report.errors.append(f"{label}: {type(exc).__name__}: {exc}")
        return None


def decide(config: Config, *, database_url: str | None = None) -> TickReport:
    """Look at the business and decide what to do. Decides only — executes nothing."""
    from .cost_resolver import resolve_all
    from .modules.analyzer import all_product_verdicts

    report = TickReport(at=datetime.now(timezone.utc).isoformat())
    database_url = database_url or config.database_url

    # 1) What is the shop selling, and do we know each product's economics?
    resolved = _safe(report, "resolve costs", lambda: resolve_all(config)) or []
    unresolved = [r for r in resolved if not r.complete()]
    if resolved:
        auto_priced = sum(1 for r in resolved if r.fully_automatic())
        report.actions.append(Action(
            "catalog.resolve_costs", AUTO,
            f"Read {len(resolved)} products from the shop; priced {auto_priced} with no "
            f"human input.",
            {"products": len(resolved), "automatic": auto_priced,
             "unresolved": [r.sku for r in unresolved]},
            result="done"))
    for r in unresolved:
        report.actions.append(Action(
            "catalog.missing_costs", BLOCKED,
            f"{r.sku}: cannot determine {', '.join(r.gaps)}, so no verdict is possible. "
            f"Frío will not guess a price.",
            {"sku": r.sku, "gaps": r.gaps}))

    # 2) Product verdicts — does each product actually make money?
    verdicts = _safe(report, "product verdicts",
                     lambda: all_product_verdicts(config, database_url)) or []
    for v in verdicts:
        decision = v.viability.decision
        if decision == "cancel":
            # Cancelling stops spend, so the agent may act. Actually pulling the ad is
            # the closed loop's job below; here it records the business decision.
            report.actions.append(Action(
                "product.cancel", AUTO,
                f"{v.title}: {v.viability.headline}",
                {"product_id": v.product_id, "pnl": v.viability.pnl}, result="decided"))
        elif decision in ("scale", "harvest"):
            report.actions.append(Action(
                f"product.{decision}", APPROVAL if decision == "scale" else AUTO,
                f"{v.title}: {v.viability.headline}",
                {"product_id": v.product_id, "pnl": v.viability.pnl,
                 "ads": v.viability.ads}))

    # 3) Ad-level closed loop — kills are automatic, scales are proposals.
    loop = _safe(report, "closed loop", lambda: _closed_loop(config, database_url))
    if loop:
        for killed in loop.get("killed", []):
            report.actions.append(Action(
                "ad.kill", AUTO, f"Killed a losing ad: {killed}", {"entity": killed},
                result="applied"))
        for scale in loop.get("scale_candidates", []):
            report.actions.append(Action(
                "ad.scale", APPROVAL,
                f"Winner worth more budget: {scale}", {"entity": scale}))
    return report


def _closed_loop(config: Config, database_url: str | None) -> dict:
    from .modules.ads import run_closed_loop

    return run_closed_loop(config, database_url=database_url)


def tick(config: Config | None = None, *, database_url: str | None = None) -> TickReport:
    """One full wake-up: decide, then carry out only what is safe to carry out.

    ``decide`` already applies the auto actions that belong to the closed loop (killing
    a loser reduces spend, which the invariant permits). Nothing marked APPROVAL is
    executed here, and there is no flag on this function that would make it execute one
    — approving is a separate, human act by construction.
    """
    return decide(config or load_config(), database_url=database_url)
