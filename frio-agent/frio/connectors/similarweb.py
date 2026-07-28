"""Similarweb discovery provider — web-traffic audience overlap ("also-visited").

Live: GET the Similarweb "also visited" / shopper-audience-overlap endpoint with
``config.similarweb_api_key``. Offline: deterministic fixtures.
"""

from __future__ import annotations

from ..config import Config
from .base import AudienceOverlap
from .fixtures import SIMILARWEB_OVERLAPS


class SimilarwebProvider:
    name = "similarweb"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.similarweb_api_key)

    def overlaps(self, seed: str, limit: int = 20) -> list[AudienceOverlap]:
        if not self.available():
            return self._offline(seed, limit)
        # Live impl (Phase 1+): call Similarweb API behind connectors.http.with_retries.
        raise NotImplementedError("wire Similarweb API call here")

    def _offline(self, seed: str, limit: int) -> list[AudienceOverlap]:
        rows = SIMILARWEB_OVERLAPS.get(seed.strip().lower(), [])
        return [
            AudienceOverlap(
                name=r["name"], overlap=r["overlap"], source=self.name,
                website=r.get("website"), meta={"offline": True},
            )
            for r in rows
        ][:limit]
