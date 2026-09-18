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


# --- Phase 2 (POD) fixtures --------------------------------------------------

# Candidate design ideas/keywords for the niche (would come from Phase 1 angles
# + eRank keyword mining in production).
POD_KEYWORD_IDEAS: dict[str, list[str]] = {
    "spirituality": [
        "manifestation journal",
        "369 method tee",
        "moon phase crystal print",
        "spiritual gangster mantra",
        "chakra alignment hoodie",
    ],
}

# Offline eRank-style demand per keyword: (search_volume, competition 0..1).
ERANK_DEMAND: dict[str, tuple[int, float]] = {
    "manifestation journal": (18000, 0.62),
    "369 method tee": (4200, 0.34),
    "moon phase crystal print": (2600, 0.41),
    "spiritual gangster mantra": (900, 0.28),
    "chakra alignment hoodie": (5400, 0.71),
}


def offline_demand(keyword: str) -> tuple[int, float]:
    return ERANK_DEMAND.get(keyword.strip().lower(), (1000, 0.5))


def offline_keyword_ideas(niche: str) -> list[str]:
    return POD_KEYWORD_IDEAS.get(niche.strip().lower(), [f"{niche} design"])


# Designs the seller ALREADY owns (would be pulled live from the TikTok Shop
# product catalog). `theme` doubles as the demand keyword.
# ``price`` + ``blank`` are here because the agent is meant to derive a product's
# economics WITHOUT anyone typing them in: price comes from the shop listing, the blank
# identifies which Printful item the cost is looked up for. The offline fixtures carry
# both so the fully-automatic path is exercised before real credentials exist.
EXISTING_DESIGNS: list[dict] = [
    {"design_id": "d-369", "title": "369 Manifestation",
     "theme": "manifestation journal", "image_uri": "shop://designs/369.png",
     "price": 29.99, "blank": "tee"},
    {"design_id": "d-moon", "title": "Moon Phases",
     "theme": "moon phase crystal print", "image_uri": "shop://designs/moon.png",
     "price": 32.00, "blank": "tee"},
    {"design_id": "d-chakra", "title": "Chakra Align",
     "theme": "chakra alignment hoodie", "image_uri": "shop://designs/chakra.png",
     "price": 54.00, "blank": "hoodie"},
    {"design_id": "d-grounded", "title": "Stay Grounded",
     "theme": "spiritual gangster mantra", "image_uri": "shop://designs/grounded.png",
     "price": 27.50, "blank": "tank"},
]

# Printful blank costs (item + print) and the shipping the seller absorbs, per blank.
# Offline stand-ins for what the Printful catalog API returns per variant, so the cost
# resolver has a real code path to exercise. Replaced by live figures once a key exists.
PRINTFUL_BLANK_COSTS: dict[str, dict] = {
    "tee": {"product_cost": 12.40, "shipping_cost": 4.69},
    "tank": {"product_cost": 11.95, "shipping_cost": 4.69},
    "hoodie": {"product_cost": 26.50, "shipping_cost": 6.99},
    "mug": {"product_cost": 7.95, "shipping_cost": 5.99},
}


def offline_blank_cost(blank: str) -> dict | None:
    return PRINTFUL_BLANK_COSTS.get((blank or "").strip().lower())

# Product FORMATS (blanks) ranked by competitor best-seller signal for the niche.
# This is where "analyze Spiritual Gangster -> sell tank tops, not tees" comes from.
COMPETITOR_FORMAT_DEMAND: dict[str, list[tuple[str, float]]] = {
    "spirituality": [
        ("tank top", 0.82),
        ("muscle tee", 0.74),
        ("tee", 0.61),
        ("hoodie", 0.47),
        ("crop top", 0.39),
    ],
}


def offline_existing_designs() -> list[dict]:
    return [dict(d) for d in EXISTING_DESIGNS]


def offline_format_demand(niche: str) -> list[tuple[str, float]]:
    return COMPETITOR_FORMAT_DEMAND.get(niche.strip().lower(), [("tee", 0.6)])
