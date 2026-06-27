"""Connector protocols + offline-mode contract.

Every external connector implements ``available()``. When its API key is absent
(or the network/SDK is unavailable) the connector runs in OFFLINE mode and
returns deterministic fixtures, so the whole Phase-1 pipeline runs end-to-end
today and real data slots in once keys are configured. Offline results are
flagged via ``meta["offline"] = True`` so callers can surface the caveat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class AudienceOverlap:
    """One competitor surfaced by a discovery provider, with an overlap score."""

    name: str
    overlap: float  # 0..1 share of the seed's audience that also engages this brand
    source: str  # similarweb | sparktoro | fastmoss
    website: str | None = None
    tiktok_handle: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class RawAd:
    """A competitor ad pulled from an ad library / creative center."""

    source: str  # creative_center | meta_ad_library | apify
    advertiser: str
    external_id: str | None = None
    media_url: str | None = None
    text: str | None = None
    raw: dict = field(default_factory=dict)


@runtime_checkable
class DiscoveryProvider(Protocol):
    """Finds brands whose audience overlaps a seed brand's audience."""

    name: str

    def available(self) -> bool: ...

    def overlaps(self, seed: str, limit: int = 20) -> list[AudienceOverlap]: ...


@runtime_checkable
class AdSource(Protocol):
    """Fetches a given advertiser's ads."""

    name: str

    def available(self) -> bool: ...

    def fetch_ads(self, advertiser: str, limit: int = 10) -> list[RawAd]: ...
