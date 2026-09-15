"""TikTok Shop webhook verification — confirmed by two independent implementations
(hookdeck/webhook-skills reference + EcomPHP/tiktokshop-php production code)."""

from __future__ import annotations

import hashlib
import hmac

from frio.connectors.tiktok_webhook import verify_webhook_signature

APP_KEY = "68abc123"
APP_SECRET = "my_app_secret"
BODY = b'{"type":17,"tts_notification_id":"7327112393057371910"}'


def _real_signature(app_key: str, app_secret: str, body: bytes) -> str:
    return hmac.new(app_secret.encode(), app_key.encode() + body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted() -> None:
    sig = _real_signature(APP_KEY, APP_SECRET, BODY)
    assert verify_webhook_signature(APP_KEY, APP_SECRET, BODY, sig) is True


def test_tampered_body_rejected() -> None:
    sig = _real_signature(APP_KEY, APP_SECRET, BODY)
    assert verify_webhook_signature(APP_KEY, APP_SECRET, BODY + b"x", sig) is False


def test_wrong_secret_rejected() -> None:
    sig = _real_signature(APP_KEY, APP_SECRET, BODY)
    assert verify_webhook_signature(APP_KEY, "different_secret", BODY, sig) is False


def test_missing_signature_rejected() -> None:
    assert verify_webhook_signature(APP_KEY, APP_SECRET, BODY, None) is False
    assert verify_webhook_signature(APP_KEY, APP_SECRET, BODY, "") is False


def test_algorithm_is_app_key_plus_body_not_body_alone() -> None:
    """The #1 documented failure mode: signing the body only, forgetting app_key."""
    body_only_sig = hmac.new(APP_SECRET.encode(), BODY, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(APP_KEY, APP_SECRET, BODY, body_only_sig) is False
