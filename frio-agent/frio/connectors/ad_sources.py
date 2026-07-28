"""Ad-research sources: TikTok Creative Center + Meta Ad Library.

Both are free, official "ground truth" for competitor ads. Live impls call the
public endpoints (behind connectors.http.with_retries); offline returns niche
fixtures so teardown/strategist run today.
"""

from __future__ import annotations

from ..config import Config
from .base import RawAd
from .fixtures import offline_ads_for


class CreativeCenterSource:
    name = "creative_center"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        # TikTok Creative Center Top Ads is public; live scraping lands in Phase 1+.
        return False

    def fetch_ads(self, advertiser: str, limit: int = 10) -> list[RawAd]:
        if not self.available():
            return self._offline(advertiser, limit)
        raise NotImplementedError("wire TikTok Creative Center fetch here")

    def _offline(self, advertiser: str, limit: int) -> list[RawAd]:
        return [
            RawAd(
                source=self.name, advertiser=advertiser, external_id=a["external_id"],
                media_url=a["media_url"], text=a["text"], raw={"offline": True},
            )
            for a in offline_ads_for(advertiser)
        ][:limit]


class MetaAdLibrarySource:
    name = "meta_ad_library"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return False

    def fetch_ads(self, advertiser: str, limit: int = 10) -> list[RawAd]:
        if not self.available():
            # Meta Ad Library offline shares the same niche fixtures, tagged by source.
            return [
                RawAd(
                    source=self.name, advertiser=advertiser, external_id=a["external_id"],
                    media_url=a["media_url"], text=a["text"], raw={"offline": True},
                )
                for a in offline_ads_for(advertiser)
            ][:limit]
        raise NotImplementedError("wire Meta Ad Library API here")
