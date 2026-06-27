"""Runtime configuration (replaces Auto-GPT's god-object Config with pydantic-settings).

All values come from env vars prefixed FRIO_ (or a .env file). The gating flags
here are what the capability registry reads to decide whether a gated/HITL
capability is available — keep money/commerce capabilities off by default.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FRIO_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Targeting ---
    niche: str = "spirituality"
    # Default seed brand for competitor discovery (see modules/competitors.py).
    seed_brands: str = "Spiritual Gangster"
    # Which pipeline's product-origin + fulfillment modules are active.
    pipeline: str = "pod"  # "pod" | "dropship"

    # --- Gating flags (default OFF — gated capabilities stay hidden) ---
    creation_enabled: bool = False      # spend money rendering AI-UGC video
    seller_approved: bool = False       # TikTok Shop seller + app approved
    ads_live_enabled: bool = False      # live ad spend allowed

    # --- Spend caps (hard ceilings enforced against the spend ledger) ---
    daily_spend_cap_usd: float = 0.0
    per_campaign_spend_cap_usd: float = 0.0
    per_clip_cost_cap_usd: float = 0.0

    # --- Product selection ---
    # Min blended demand-vs-competition score (0..1) for a POD design to pass.
    demand_threshold: float = 0.2
    pod_blank: str = "tee"  # default blank product for mockups

    # --- Data ---
    database_url: str = "sqlite:///frio.db"

    # --- Credentials (optional; absent => related connectors are inert) ---
    anthropic_api_key: str | None = None
    similarweb_api_key: str | None = None
    fastmoss_api_key: str | None = None
    printful_api_key: str | None = None
    tiktok_shop_api_key: str | None = None
    tiktok_ads_api_key: str | None = None


def load_config() -> Config:
    return Config()
