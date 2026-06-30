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
    per_clip_cost_cap_usd: float = 0.0   # per AI-UGC video clip
    per_image_cost_cap_usd: float = 0.0  # per AI-UGC image (carousel slide)

    # --- Product selection ---
    # Min blended demand-vs-competition score (0..1) for a POD design to pass.
    demand_threshold: float = 0.2
    pod_blank: str = "tee"  # default blank product for mockups

    # --- Optimize engine (kill/scale thresholds; in config, not code) ---
    opt_kill_spend_no_atc_usd: float = 20.0   # spend with 0 add-to-carts -> kill
    opt_kill_ctr_min: float = 0.01            # CTR floor (1%)
    opt_kill_min_impressions: int = 1000      # min impressions before CTR judged
    opt_target_cpa_usd: float = 0.0           # 0 = disabled
    opt_kill_cpa_multiple: float = 3.0        # CPA > N x target -> kill
    opt_scale_mer_min: float = 2.0            # MER at/above -> scale candidate
    opt_scale_min_purchases: int = 3          # need real conversions before scaling
    opt_scale_budget_step_pct: float = 0.20   # +20% per scale step
    # Statistical rigor (fewer false kills; Thompson budget allocation)
    opt_use_statistical_ctr: bool = True      # kill on CTR only if confidently below floor
    opt_ctr_confidence_z: float = 1.96        # 95% (Wilson upper bound)
    opt_scale_pool_usd: float = 0.0           # if >0, Thompson-allocate this pool to winners

    # --- Financial / commercial analyzer (product viability) ---
    fin_platform_fee_pct: float = 0.08   # TikTok Shop apparel referral (incl. US pay proc)
    fin_payment_fee_pct: float = 0.0
    fin_default_return_rate: float = 0.0
    fin_target_poas: float = 1.5         # healthy ad-profitability
    fin_scale_poas: float = 2.0          # strong enough to scale
    fin_min_units: int = 10              # min sales before a verdict is trusted
    fin_test_spend_usd: float = 50.0     # min ad spend for a fair product test

    # --- Compliance (ad-policy claims scan is active; AI-UGC disclosure DEFERRED) ---
    # NOTE: FTC AI-UGC disclosure is intentionally OFF for now (revisit later — see
    # NOTES "Deferred"). The prohibited-claims scan stays on.
    require_ai_disclosure: bool = False
    ai_disclosure_text: str = "AI-generated • results not guaranteed"

    # --- Data ---
    database_url: str = "sqlite:///frio.db"

    # --- Dashboard (private, login-protected; IntoSpirit) ---
    dashboard_user: str = "frio"
    dashboard_password: str | None = None       # login password (must be set to start)
    dashboard_session_secret: str | None = None  # signs session cookies (set in prod)
    dashboard_secure_cookies: bool = True        # set 0 only for local http testing
    dashboard_brand: str = "IntoSpirit"

    # --- Credentials (optional; absent => related connectors are inert) ---
    anthropic_api_key: str | None = None
    similarweb_api_key: str | None = None
    fastmoss_api_key: str | None = None
    printful_api_key: str | None = None  # POD fulfillment
    cj_api_key: str | None = None  # Dropshipping fulfillment (CJ Dropshipping)
    fal_api_key: str | None = None  # video gen: one key -> Veo/Kling/Runway via fal.ai
    higgsfield_api_key: str | None = None  # video+image: Nano Banana/Soul/Seedance via MCP
    video_provider: str = "veo"  # veo | kling | runway | prizmad | arcads
    image_provider: str = "nano_banana"  # nano_banana | soul | flux | gpt_image
    tiktok_shop_api_key: str | None = None
    tiktok_ads_api_key: str | None = None


def load_config() -> Config:
    return Config()
