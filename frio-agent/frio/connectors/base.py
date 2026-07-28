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


# --- Phase 2 (POD product origin) -------------------------------------------


@dataclass
class DemandSignal:
    """Search-demand validation for a keyword/design idea (Etsy/eRank style)."""

    keyword: str
    search_volume: int
    competition: float  # 0..1 (higher = more saturated)
    source: str  # erank | everbee | marmalead
    score: float = 0.0  # 0..1 blended demand-vs-competition score
    meta: dict = field(default_factory=dict)


@dataclass
class DesignAsset:
    """A generated design (image) for a POD product."""

    prompt: str
    uri: str | None
    provider: str  # dalle | ideogram | midjourney
    meta: dict = field(default_factory=dict)


@dataclass
class MockupAsset:
    """A product mockup rendered from a design."""

    design_uri: str | None
    uri: str | None
    blank: str  # e.g. "tee", "hoodie"
    provider: str  # printful | automated_mockups | dynamic_mockups
    meta: dict = field(default_factory=dict)


@runtime_checkable
class DemandProvider(Protocol):
    """Validates search demand for a keyword/design idea."""

    name: str

    def available(self) -> bool: ...

    def validate(self, keyword: str) -> DemandSignal: ...


@runtime_checkable
class DesignGenerator(Protocol):
    """Generates a design image from a prompt."""

    name: str

    def available(self) -> bool: ...

    def generate(self, prompt: str) -> DesignAsset: ...


@runtime_checkable
class MockupGenerator(Protocol):
    """Renders a product mockup from a design."""

    name: str

    def available(self) -> bool: ...

    def render(self, design: DesignAsset, blank: str = "tee") -> MockupAsset: ...
