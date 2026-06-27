"""SparkToro discovery provider — social audience research.

"What do people who follow the seed brand also follow/watch?" Live: SparkToro
audience API with ``config`` credentials. Offline: deterministic fixtures.
"""

from __future__ import annotations

from ..config import Config
from .base import AudienceOverlap
from .fixtures import SPARKTORO_OVERLAPS


class SparkToroProvider:
    name = "sparktoro"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        # SparkToro has no dedicated key field yet; treat as offline-only for now.
        return False

    def overlaps(self, seed: str, limit: int = 20) -> list[AudienceOverlap]:
        if not self.available():
            return self._offline(seed, limit)
        raise NotImplementedError("wire SparkToro API call here")

    def _offline(self, seed: str, limit: int) -> list[AudienceOverlap]:
        rows = SPARKTORO_OVERLAPS.get(seed.strip().lower(), [])
        return [
            AudienceOverlap(
                name=r["name"], overlap=r["overlap"], source=self.name,
                tiktok_handle=r.get("tiktok_handle"), meta={"offline": True},
            )
            for r in rows
        ][:limit]
