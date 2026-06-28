"""Statistics for the optimize engine (no heavy deps).

- Wilson score interval: confidence bounds on a rate (CTR, CVR) that stay honest
  on small samples — so we only kill a creative when we're *confident* its true
  rate is below the floor, not just because a noisy point estimate dipped.
- Thompson sampling: allocate a budget pool across winners by sampling each arm's
  Beta posterior, balancing exploration (uncertain arms) and exploitation (proven).
"""

from __future__ import annotations

import math
import random

# z-scores for common confidence levels.
Z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    denom = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denom
    margin = (z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def wilson_upper_bound(successes: int, trials: int, z: float = 1.96) -> float:
    return wilson_interval(successes, trials, z)[1]


def wilson_lower_bound(successes: int, trials: int, z: float = 1.96) -> float:
    return wilson_interval(successes, trials, z)[0]


def thompson_allocation(arms: list[tuple[str, int, int]], total_budget: float,
                        seed: int = 0) -> dict[str, float]:
    """Split ``total_budget`` across arms = [(id, successes, trials), ...].

    Each arm's share ∝ a draw from Beta(successes+1, failures+1); proven winners
    get more, but uncertain arms still get exploration budget. Seeded for
    reproducibility.
    """
    if not arms or total_budget <= 0:
        return {}
    rng = random.Random(seed)
    samples = {}
    for aid, succ, trials in arms:
        succ = max(0, succ)
        failures = max(0, trials - succ)
        samples[aid] = rng.betavariate(succ + 1, failures + 1)
    total = sum(samples.values()) or 1.0
    return {aid: round(total_budget * v / total, 2) for aid, v in samples.items()}
