"""TikTok Shop webhook signature verification.

A DIFFERENT algorithm from request signing (tiktok_sign.py) — do not confuse them.
Confirmed by TWO independent sources (2026-09-15 research):
  - hookdeck/webhook-skills (MIT) — reference doc + example code.
  - EcomPHP/tiktokshop-php (Apache-2.0) -> src/Webhook.php — real production code,
    byte-for-byte the same construction.

Algorithm:
  signature = HMAC-SHA256(key=app_secret, message=app_key + raw_request_body)
  -> lowercase hex, delivered in the ``Authorization`` HEADER with NO "Bearer" prefix.

Honesty note: TikTok's own "TikTok Shop webhooks" overview page was confirmed to be an
EMPTY STUB in the source mirror (content_length: 0 in the scraper's own metadata) — this
gap is in TikTok's documentation itself, not a research failure. The construction above
rests on the two independent sources above, not on TikTok's own worked example (none
was found). Re-verify empirically against a real webhook delivery once an app exists.

There is NO TIMESTAMP in this signature -> no built-in replay protection. Dedupe
incoming webhooks by ``tts_notification_id`` (present in every webhook payload).
"""

from __future__ import annotations

import hashlib
import hmac


def verify_webhook_signature(app_key: str, app_secret: str,
                             raw_body: bytes, signature: str) -> bool:
    """Return True iff ``signature`` (the raw ``Authorization`` header value, no
    "Bearer" prefix) matches the HMAC-SHA256 of ``app_key + raw_body``.

    ``raw_body`` MUST be the exact bytes received on the wire — do not parse and
    re-serialize JSON first (the same trap as request signing: re-serialization
    changes whitespace/key order and breaks the HMAC).
    """
    expected = hmac.new(app_secret.encode(),
                        app_key.encode() + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
