"""Offline fixtures for the spirituality/wellbeing niche.

Used when API keys are absent so the pipeline runs end-to-end. These mimic the
*shape* of real provider responses; swap for live data by configuring keys.
"""

from __future__ import annotations

# Audience-overlap fixtures per seed brand, split across providers to simulate
# multi-source discovery (Similarweb = web traffic overlap, SparkToro = social).
SIMILARWEB_OVERLAPS: dict[str, list[dict]] = {
    "spiritual gangster": [
        {"name": "Wanderlust", "overlap": 0.74, "website": "wanderlust.com"},
        {"name": "Alo Yoga", "overlap": 0.66, "website": "aloyoga.com"},
        {"name": "Gaiam", "overlap": 0.52, "website": "gaiam.com"},
    ],
}

SPARKTORO_OVERLAPS: dict[str, list[dict]] = {
    "spiritual gangster": [
        {"name": "Manifestation Co", "overlap": 0.61, "tiktok_handle": "@manifestationco"},
        {"name": "The Mindful Collective", "overlap": 0.49, "tiktok_handle": "@mindfulco"},
        {"name": "Alo Yoga", "overlap": 0.58, "tiktok_handle": "@aloyoga"},
    ],
}

# A couple of representative ads per advertiser (spirituality angle).
ADS: dict[str, list[dict]] = {
    "wanderlust": [
        {
            "external_id": "wl-001",
            "text": "POV: you finally stopped chasing and started attracting. "
            "Our mantra tee is your daily reminder. Tap to manifest.",
            "media_url": "https://example/wl-001.mp4",
        },
    ],
    "alo yoga": [
        {
            "external_id": "alo-001",
            "text": "Your morning ritual just got an upgrade ✨ soft, grounding, "
            "made to move. Limited drop — link in bio.",
            "media_url": "https://example/alo-001.mp4",
        },
    ],
    "manifestation co": [
        {
            "external_id": "mco-001",
            "text": "Stop scrolling. This is your sign. The 369 journal that "
            "changed everything — 10k sold this week.",
            "media_url": "https://example/mco-001.mp4",
        },
    ],
}


def offline_ads_for(advertiser: str) -> list[dict]:
    return ADS.get(advertiser.strip().lower(), [
        {
            "external_id": None,
            "text": f"{advertiser}: aspirational hook → product reveal → soft CTA.",
            "media_url": None,
        }
    ])
