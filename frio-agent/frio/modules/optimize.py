"""Phase 4 — Optimize engine (deterministic kill/scale rules).

The money brain. Pure deterministic code — the LLM is NEVER in this path. It
reads computed metrics and emits PROPOSALS:

  - KILL   (reduces spend) -> auto-executable; safe to apply automatically.
  - SCALE  (increases spend) -> requires human approval before it can apply.
  - HOLD   -> no action / insufficient data.

Thresholds come from Config (not hardcoded). Proposals are recorded in the
append-only `decisions` audit log. Actual application to a live ad account is
Phase 6 — here we only measure + propose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..capabilities import capability
from ..config import Config, load_config
from ..db.base import make_session_factory
from ..db.models import Decision
from ..metrics import EntityMetrics, aggregate_all
from ..stats import thompson_allocation, wilson_upper_bound


@dataclass
class Proposal:
    entity_type: str
    entity_id: str
    action: str  # kill | scale | hold
    reason: str
    auto_executable: bool  # True only for spend-reducing actions (kills)
    budget_change_pct: float  # -1.0 = off, +0.20 = scale up, 0 = hold
    metrics: dict


def evaluate(m: EntityMetrics, config: Config) -> Proposal:
    """Apply kill rules first (spend-reducing), then scale, else hold."""
    base = dict(entity_type=m.entity_type, entity_id=m.entity_id, metrics=m.snapshot())

    # --- KILL rules (auto-executable; they only ever reduce spend) ---
    if m.spend_usd >= config.opt_kill_spend_no_atc_usd and m.add_to_carts == 0:
        return Proposal(action="kill", auto_executable=True, budget_change_pct=-1.0,
                        reason=f"${m.spend_usd:.0f} spent with 0 add-to-carts "
                               f"(>= ${config.opt_kill_spend_no_atc_usd:.0f}).", **base)

    if m.impressions >= config.opt_kill_min_impressions:
        if config.opt_use_statistical_ctr:
            # Only kill when we're CONFIDENT the true CTR is below the floor — the
            # Wilson upper bound stays wide on noisy samples, avoiding false kills.
            ub = wilson_upper_bound(m.clicks, m.impressions, config.opt_ctr_confidence_z)
            confident_below = ub < config.opt_kill_ctr_min
            stat = f" (95% upper bound {ub*100:.2f}%)"
        else:
            confident_below = m.ctr < config.opt_kill_ctr_min
            stat = ""
        if confident_below:
            return Proposal(action="kill", auto_executable=True, budget_change_pct=-1.0,
                            reason=f"CTR {m.ctr*100:.2f}% < {config.opt_kill_ctr_min*100:.0f}%"
                                   f"{stat} after {m.impressions} impressions.", **base)

    if (config.opt_target_cpa_usd > 0 and m.cpa is not None
            and m.cpa > config.opt_kill_cpa_multiple * config.opt_target_cpa_usd):
        return Proposal(action="kill", auto_executable=True, budget_change_pct=-1.0,
                        reason=f"CPA ${m.cpa:.2f} > {config.opt_kill_cpa_multiple:g}x target "
                               f"${config.opt_target_cpa_usd:.2f}.", **base)

    # --- SCALE rule (increases spend -> requires human approval) ---
    if m.purchases >= config.opt_scale_min_purchases and m.mer >= config.opt_scale_mer_min:
        return Proposal(action="scale", auto_executable=False,
                        budget_change_pct=config.opt_scale_budget_step_pct,
                        reason=f"MER {m.mer:.2f} >= {config.opt_scale_mer_min:g} on "
                               f"{m.purchases} purchases — scale +"
                               f"{config.opt_scale_budget_step_pct*100:.0f}% (needs approval).",
                        **base)

    # --- HOLD ---
    return Proposal(action="hold", auto_executable=False, budget_change_pct=0.0,
                    reason="No kill/scale threshold met (holding / gathering data).", **base)


def _window_stats(rows: list[dict]) -> dict:
    imp = sum(r["impressions"] for r in rows)
    clicks = sum(r["clicks"] for r in rows)
    spend = sum(r["spend_usd"] for r in rows)
    rev = sum(r["revenue_usd"] for r in rows)
    freqs = [r["frequency"] for r in rows if r["frequency"] > 0]
    return {"impressions": imp, "ctr": clicks / imp if imp else 0.0, "spend": spend,
            "mer": rev / spend if spend else 0.0,
            "frequency": sum(freqs) / len(freqs) if freqs else 0.0}


def detect_fatigue(series: list[dict], config: Config) -> str | None:
    """Creative fatigue: recent CTR well below its own baseline, or frequency too high.

    CTR degrades days before CPA does — this is the early-warning that a WINNING
    creative is wearing out (TikTok fatigues ~4x faster than Meta). Returns the
    reason string, or None. Deterministic; needs enough daily history.
    """
    n = config.opt_fatigue_recent_days
    if len(series) < n * 2:  # need a baseline AND a recent window
        return None
    baseline, recent = _window_stats(series[:-n]), _window_stats(series[-n:])
    if (baseline["impressions"] < config.opt_fatigue_min_impressions
            or recent["impressions"] < config.opt_fatigue_min_impressions):
        return None
    if recent["frequency"] > config.opt_fatigue_frequency_max:
        return (f"Frequency {recent['frequency']:.1f} > "
                f"{config.opt_fatigue_frequency_max:g} — audience saturated.")
    if baseline["ctr"] > 0 and recent["ctr"] < baseline["ctr"] * (1 - config.opt_fatigue_ctr_drop):
        return (f"CTR {recent['ctr']*100:.2f}% is {config.opt_fatigue_ctr_drop*100:.0f}%+ "
                f"below its own baseline {baseline['ctr']*100:.2f}% — creative wearing out.")
    return None


def detect_scaling_plateau(series: list[dict], config: Config) -> str | None:
    """Diminishing returns: spend rose but efficiency (MER) fell — stop scaling.

    Judges the MARGINAL return (recent window vs baseline), not the blended
    average, which masks inefficiency at the margin. Returns reason or None.
    """
    if len(series) < 4:
        return None
    half = len(series) // 2
    base, recent = _window_stats(series[:half]), _window_stats(series[half:])
    if base["spend"] <= 0 or base["mer"] <= 0:
        return None
    spend_up = recent["spend"] >= base["spend"] * (1 + config.opt_plateau_spend_rise)
    mer_down = recent["mer"] <= base["mer"] * (1 - config.opt_plateau_mer_drop)
    if spend_up and mer_down:
        return (f"Spend up {((recent['spend']/base['spend'])-1)*100:.0f}% but MER fell "
                f"{base['mer']:.2f}→{recent['mer']:.2f} — diminishing returns; hold at the "
                f"last efficient budget and scale horizontally instead.")
    return None


def propose_all(session, config: Config, entity_type: str = "creative") -> list[Proposal]:
    """Evaluate every entity, layering fatigue/plateau signals over the base rules.

    Priority: KILL (safety) > REFRESH (fatigue) > plateau-veto on SCALE > base action.
    """
    from ..metrics import daily_series

    out: list[Proposal] = []
    for m in aggregate_all(session, entity_type):
        p = evaluate(m, config)
        if p.action != "kill":  # kills always win — they're the safety rail
            series = daily_series(session, entity_type, m.entity_id)
            fatigue = detect_fatigue(series, config)
            if fatigue:
                # Rotating creative implies producing a replacement (costs money),
                # so refresh is a recommendation, never auto-executed.
                p = Proposal(action="refresh", auto_executable=False,
                             budget_change_pct=0.0,
                             reason=f"Creative fatigue: {fatigue} Rotate/replace the "
                                    f"creative (e.g. swap the hook/first 3s).",
                             entity_type=m.entity_type, entity_id=m.entity_id,
                             metrics=m.snapshot())
            elif p.action == "scale":
                plateau = detect_scaling_plateau(series, config)
                if plateau:
                    p = Proposal(action="hold", auto_executable=False,
                                 budget_change_pct=0.0,
                                 reason=f"Stop scaling: {plateau}",
                                 entity_type=m.entity_type, entity_id=m.entity_id,
                                 metrics=m.snapshot())
        out.append(p)
    return out


def record_proposals(session, proposals: list[Proposal]) -> None:
    """Append each proposal to the decisions audit log."""
    for p in proposals:
        session.add(Decision(
            kind=p.action, actor="engine", target=p.entity_id, rationale=p.reason,
            payload={"auto_executable": p.auto_executable,
                     "budget_change_pct": p.budget_change_pct, "metrics": p.metrics},
        ))


def allocate_scale_budget(session, config: Config, total_budget: float, *,
                          entity_type: str = "creative", seed: int = 0) -> dict[str, float]:
    """Thompson-sample a budget pool across the current scale winners.

    Uses each winner's Beta posterior on conversion (purchases/clicks) so proven
    performers get more, while still exploring promising-but-uncertain ones.
    """
    winners = [m for m in aggregate_all(session, entity_type)
               if evaluate(m, config).action == "scale"]
    arms = [(m.entity_id, m.purchases, m.clicks) for m in winners]
    return thompson_allocation(arms, total_budget, seed=seed)


def cadence_focus(week: int) -> str:
    """The researched 4-week testing cadence."""
    return {
        1: "Test 5 audiences x 3 creatives (15 ad sets), ABO.",
        2: "Kill bottom 80%, scale top 20% into CBO.",
        3: "Launch lookalikes from converters; refresh hooks.",
        4: "Budget up winners only (~+20% every 3 days).",
    }.get(week, "Steady-state: keep killing losers, scaling winners.")


@capability(
    "optimize.evaluate",
    "Evaluate ad metrics and propose kill/scale/hold (deterministic; no spend).",
    parameters={"entity_type": {"type": "string", "required": False}},
    category="optimize",
)
def _cap_evaluate(database_url: str | None = None, entity_type: str = "creative",
                  config: Config | None = None) -> list[dict]:
    config = config or load_config()
    Session = make_session_factory(database_url or config.database_url)
    with Session() as s:
        return [asdict(p) for p in propose_all(s, config, entity_type)]
