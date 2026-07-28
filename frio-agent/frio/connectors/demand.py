"""Demand validation — eRank-style Etsy search-demand for a keyword.

Validate demand BEFORE designing (the POD discipline). Live: eRank/Everbee API.
Offline: deterministic fixtures. ``score`` blends demand vs competition into 0..1.
"""

from __future__ import annotations

from ..config import Config
from .base import DemandSignal
from .fixtures import offline_demand


def demand_score(search_volume: int, competition: float) -> float:
    """High volume + low competition => high score. Normalized to 0..1."""
    import math

    volume_factor = min(1.0, math.log10(max(search_volume, 1)) / 5.0)  # ~100k -> 1.0
    return round(volume_factor * (1.0 - competition), 3)


class ErankProvider:
    name = "erank"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        # No dedicated key field yet; eRank has no public API, treat as offline.
        return False

    def validate(self, keyword: str) -> DemandSignal:
        if not self.available():
            volume, comp = offline_demand(keyword)
            return DemandSignal(
                keyword=keyword, search_volume=volume, competition=comp,
                source=self.name, score=demand_score(volume, comp),
                meta={"offline": True},
            )
        raise NotImplementedError("wire eRank/Everbee API here")
