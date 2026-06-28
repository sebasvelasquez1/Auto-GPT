"""TikTok Ads connector — launch / pause / set-budget on campaigns.

Live: the official tiktok-business-api-sdk (or an ads MCP) behind
``tiktok_ads_api_key``. Offline returns placeholder ids/acks so the closed loop
runs without a real ad account. Spend-cap enforcement + HITL live one layer up in
``modules/ads.py`` — this connector just does the I/O.
"""

from __future__ import annotations

import hashlib

from ..config import Config


def _slug(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:10]


class TikTokAdsConnector:
    name = "tiktok_ads"

    def __init__(self, config: Config) -> None:
        self._config = config

    def available(self) -> bool:
        return bool(self._config.tiktok_ads_api_key)

    def launch_campaign(self, name: str, daily_budget_usd: float) -> str:
        if not self.available():
            return f"ttc-offline-{_slug(name)}"
        raise NotImplementedError("wire tiktok-business-api-sdk campaign creation here")

    def pause_campaign(self, external_id: str) -> dict:
        if not self.available():
            return {"external_id": external_id, "status": "paused_offline"}
        raise NotImplementedError("wire TikTok Ads campaign pause here")

    def set_budget(self, external_id: str, new_daily_budget_usd: float) -> dict:
        if not self.available():
            return {"external_id": external_id, "status": "budget_set_offline",
                    "daily_budget_usd": new_daily_budget_usd}
        raise NotImplementedError("wire TikTok Ads budget update here")
