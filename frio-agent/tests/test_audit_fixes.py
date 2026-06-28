"""Regression tests for issues found in the architecture/spend-safety audit."""

from __future__ import annotations

from frio.config import Config
from frio.modules import creation
from frio.pipeline import run_phase3, run_phase3_carousel
from frio.stats import thompson_allocation, wilson_interval, wilson_upper_bound


# --- P0: in-memory engine isolation (init_db + session must share one engine) ---

def test_render_video_in_memory_db_does_not_crash() -> None:
    # Previously raised "no such table: spend_ledger" because init_db and the
    # session used two separate in-memory databases.
    out = creation.render_video({"hook": "h", "video_prompt": "p"},
                                Config(creation_enabled=True), approve=True,
                                database_url="sqlite://")
    assert out["approved"] is True and out["cost_usd"] == 0.0


def test_run_phase3_persist_false_renders() -> None:
    res = run_phase3(config=Config(creation_enabled=True, database_url="sqlite://"),
                     approve=True, persist=False)
    assert res.rendered is not None
    assert res.gate_message is None


def test_run_phase3_carousel_persist_false_renders() -> None:
    res = run_phase3_carousel(config=Config(creation_enabled=True, database_url="sqlite://"),
                              slides=3, approve=True, persist=False)
    assert res.rendered is not None and len(res.rendered["slides"]) == 3


# --- stats defensive guards (garbage in -> no crash) ---

def test_wilson_handles_bad_inputs() -> None:
    assert wilson_interval(5, 0) == (0.0, 1.0)        # no trials
    assert wilson_interval(-1, 100) == (0.0, 1.0)     # negative successes
    # successes > trials is clamped, not a math-domain crash
    ub = wilson_upper_bound(150, 100)
    assert 0.0 <= ub <= 1.0


def test_thompson_handles_successes_over_trials() -> None:
    alloc = thompson_allocation([("a", 150, 100), ("b", 1, 100)], 100.0, seed=0)
    assert abs(sum(alloc.values()) - 100.0) < 0.05
    assert all(v >= 0 for v in alloc.values())
