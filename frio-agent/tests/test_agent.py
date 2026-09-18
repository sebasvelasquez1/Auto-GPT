"""The autonomous runner: it decides and acts by itself, and stops at every spend.

Built 2026-09-18 because the owner was right that it was missing — the package had
capabilities but nothing that woke up and used them. These tests pin the two properties
that make it safe to leave running unattended:

  1. It really does act on its own (no human input in the decision path).
  2. It can NEVER execute a spend-increasing action, whatever the inputs say.
"""

from __future__ import annotations

from frio import agent
from frio.agent import APPROVAL, AUTO, BLOCKED, Action, TickReport, decide, tick
from frio.config import Config


class _Viability:
    def __init__(self, decision, headline="h"):
        self.decision, self.headline = decision, headline
        self.reasons, self.pnl, self.ads = [], {}, None


class _Verdict:
    def __init__(self, decision, title="P", pid=1):
        self.product_id, self.title, self.kind, self.blank = pid, title, "pod", "tee"
        self.viability = _Viability(decision)


def _patch(monkeypatch, *, verdicts=(), loop=None, resolved=()):
    monkeypatch.setattr("frio.modules.analyzer.all_product_verdicts",
                        lambda *a, **k: list(verdicts))
    monkeypatch.setattr("frio.cost_resolver.resolve_all", lambda *a, **k: list(resolved))
    monkeypatch.setattr(agent, "_closed_loop", lambda *a, **k: loop or {})


# --- It acts on its own -----------------------------------------------------------

def test_a_tick_needs_no_human_input_at_all(monkeypatch) -> None:
    _patch(monkeypatch, verdicts=[_Verdict("cancel")])
    report = tick(Config())
    assert isinstance(report, TickReport)
    assert any(a.name == "product.cancel" and a.mode == AUTO for a in report.actions)


def test_it_reads_the_shop_rather_than_a_supplied_list(monkeypatch) -> None:
    class R:
        sku, gaps = "a", []
        def complete(self): return True
        def fully_automatic(self): return True

    _patch(monkeypatch, resolved=[R()])
    names = [a.name for a in tick(Config()).actions]
    assert "catalog.resolve_costs" in names


# --- It stops at every spend ------------------------------------------------------

def test_scaling_a_winner_is_queued_for_a_human_never_executed(monkeypatch) -> None:
    _patch(monkeypatch, verdicts=[_Verdict("scale", "Winner")])
    report = tick(Config())
    scale = next(a for a in report.actions if a.name == "product.scale")
    assert scale.mode == APPROVAL
    assert scale.result is None          # nothing was carried out
    assert scale not in report.executed()


def test_killing_a_loser_runs_automatically(monkeypatch) -> None:
    """The asymmetry: stopping spend is safe, so it does not wait for anyone."""
    _patch(monkeypatch, loop={"killed": ["ad-1"]})
    killed = next(a for a in tick(Config()).actions if a.name == "ad.kill")
    assert killed.mode == AUTO and killed.result == "applied"


def test_an_ad_scale_proposal_is_also_only_a_proposal(monkeypatch) -> None:
    _patch(monkeypatch, loop={"scale_candidates": ["ad-9"]})
    scale = next(a for a in tick(Config()).actions if a.name == "ad.scale")
    assert scale.mode == APPROVAL and scale.result is None


def test_no_executed_action_ever_increases_spend(monkeypatch) -> None:
    """The invariant, asserted over a tick containing every action type at once."""
    _patch(monkeypatch,
           verdicts=[_Verdict("scale", "W", 1), _Verdict("cancel", "L", 2),
                     _Verdict("harvest", "H", 3)],
           loop={"killed": ["ad-1"], "scale_candidates": ["ad-9"]})
    report = tick(Config())
    spend_increasing = {"product.scale", "ad.scale"}
    assert not [a for a in report.executed() if a.name in spend_increasing]
    assert {a.name for a in report.awaiting_human()} == spend_increasing


# --- It survives a broken world ---------------------------------------------------

def test_one_broken_step_does_not_kill_the_tick(monkeypatch) -> None:
    """An agent that dies on the first error silently stops running the business."""
    def boom(*a, **k):
        raise RuntimeError("database is down")

    monkeypatch.setattr("frio.modules.analyzer.all_product_verdicts", boom)
    monkeypatch.setattr("frio.cost_resolver.resolve_all", lambda *a, **k: [])
    monkeypatch.setattr(agent, "_closed_loop", lambda *a, **k: {"killed": ["ad-1"]})
    report = tick(Config())
    assert any("database is down" in e for e in report.errors)   # recorded
    assert any(a.name == "ad.kill" for a in report.actions)      # and it carried on


def test_a_product_with_unknowable_costs_is_blocked_not_guessed(monkeypatch) -> None:
    class R:
        sku, gaps = "ghost", ["price"]
        def complete(self): return False
        def fully_automatic(self): return False

    _patch(monkeypatch, resolved=[R()])
    blocked = next(a for a in tick(Config()).actions if a.name == "catalog.missing_costs")
    assert blocked.mode == BLOCKED and "will not guess" in blocked.reason


def test_the_report_is_an_audit_trail(monkeypatch) -> None:
    """Every decision has to be explainable after the fact, with its reason."""
    _patch(monkeypatch, verdicts=[_Verdict("cancel", "Loser")])
    snap = tick(Config()).snapshot()
    assert snap["at"] and snap["counts"]["executed"] >= 1
    assert all(a["reason"] for a in snap["actions"])


def test_an_empty_business_produces_an_empty_tick(monkeypatch) -> None:
    _patch(monkeypatch)
    report = decide(Config())
    assert report.actions == [] and report.errors == []
