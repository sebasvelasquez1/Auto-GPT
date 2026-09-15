"""TikTok Shop API request signing.

VERIFIED algorithm — not guessed. The project rule forbids guessing crypto, so this
rests on a first-party source plus reproduced test vectors:
  - PRIMARY: TikTok's own MIT-licensed reference implementation,
    github.com/tiktok/ttspc-server-sample -> src/utils/sign.ts ((c) 2026 TikTok).
  - Cross-checked against 3 independent implementations in other languages
    (EcomPHP/tiktokshop-php Apache-2.0; hsib19/tiktok-shop-sdk MIT; plus others).
  - Reproduced locally against two published test vectors (tests/test_tiktok_sign.py).

NOTE on the official sample: it declares excludeKeys = [access_token, sign] but leaves
the filtering line COMMENTED OUT — it expects the caller to pre-filter. We filter
explicitly below, and test_sign_and_access_token_are_excluded pins that behaviour.

RESOLVED (2026-09-15): the "v2" signing format is NOT a real second TikTok Shop scheme.
Read directly in hsib19/tiktok-shop-sdk's own source: signature.ts implements an
optional version:'v1'|'v2' branch, but Request.ts HARDCODES version:'v1' with the
comment "Signature version 'v1' is used explicitly here" — v2 is that SDK author's own
unused, speculative code, never actually invoked. v1 (implemented below) is the only
real algorithm, independently confirmed by FOUR implementations: TikTok's own official
sample, EcomPHP (PHP), hsib19 (TypeScript, v1 path), and fudiwei (C#).

Algorithm (TikTok Shop Open API, 202309+):
  1. Take all query params EXCEPT ``sign`` and ``access_token``.
  2. Sort keys ascending (ASCII/lexicographic).
  3. Concatenate ``key1value1key2value2`` — no '=', no '&', no URL-encoding.
  4. Prepend the request path (e.g. ``/order/202309/orders/search``).
  5. Append the RAW JSON body, unless content-type is multipart/form-data.
  6. Wrap: ``app_secret + string + app_secret``.
  7. HMAC-SHA256 keyed by app_secret -> lowercase hex.

Traps this module is built to avoid (each cost someone a debugging day):
  - Sign the EXACT bytes transmitted. Serialize JSON once to bytes, sign those
    bytes, POST those bytes. If an HTTP library re-serializes a dict, key order or
    spacing changes and the signature silently breaks.
  - The auth endpoints live on a DIFFERENT host and are NOT signed
    (auth.tiktok-shops.com/api/v2/token/get|refresh take plain query params). Uses the
    non-standard grant_type=authorized_code (NOT "authorization_code") — confirmed
    identical in two independent SDKs (EcomPHP and hsib19).
  - ``shop_cipher`` is REQUIRED for TikTok Shops in China enabled for cross-border sales,
    but OPTIONAL for local shops in US/UK/SEA markets (per TikTok's own "Connecting
    shops" use-case doc) — and is FORBIDDEN on /authorization/*, /seller/* and upload
    endpoints (confirmed via EcomPHP's shop_cipher-exclusion regex, which also covers
    /product/{id}/compliance, /product/{id}/global_products, /product/{id}/files/upload,
    /product/{id}/images/upload, and POST /product/{id}/brands).
  - timestamp is 10-digit Unix SECONDS and must be within 5 minutes of server time.
  - EMPTY-VALUE query params must be stripped before signing AND before sending (they
    do not participate in the signature). Confirmed in fudiwei's C# SDK:
    "过滤空参数，空参数不参与签名" (filter empty params, they don't participate in
    signing) — removes them from both the request and the sign base string.
  - Access token lifetime is 7 DAYS by default per TikTok's own docs
    ("auth-overview-202407" and "generate-test-token"), not 24 hours as some
    third-party blogs claim — no primary source supports the 24h figure for Shop
    (the TikTok ADS access token is the one that's 24h; don't conflate the two APIs).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

API_HOST = "https://open-api.tiktokglobalshop.com"
AUTH_HOST = "https://auth.tiktok-shops.com"  # token get/refresh — unsigned


def sign_request(app_secret: str, path: str, query_params: dict,
                 body: bytes = b"", content_type: str = "application/json") -> str:
    """Return the lowercase-hex ``sign`` value for one request.

    Empty-value params are excluded from the signature (confirmed in fudiwei's C#
    SDK) — the caller must also omit them from the actual request, or the signature
    computed here will not match what a strict server-side check expects.
    """
    keys = sorted(k for k in query_params
                 if k not in ("sign", "access_token") and query_params[k] not in ("", None))
    canonical = path + "".join(f"{k}{query_params[k]}" for k in keys)
    if body and "multipart/form-data" not in (content_type or ""):
        canonical += body.decode("utf-8")
    canonical = f"{app_secret}{canonical}{app_secret}"
    return hmac.new(app_secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def prepare_call(app_key: str, app_secret: str, path: str, *,
                 access_token: str | None = None, shop_cipher: str | None = None,
                 params: dict | None = None, body: dict | None = None,
                 timestamp: int | None = None) -> dict:
    """Build a ready-to-send signed request.

    Returns {url, params, headers, body} where ``body`` is the exact bytes that were
    signed — send THOSE bytes, never a re-serialized dict (see module docstring).
    """
    query = {k: v for k, v in (params or {}).items() if v not in ("", None)}
    query["app_key"] = app_key
    query["timestamp"] = str(timestamp if timestamp is not None else int(time.time()))
    if shop_cipher:
        query["shop_cipher"] = shop_cipher

    body_bytes = json.dumps(body, separators=(",", ":")).encode() if body else b""
    query["sign"] = sign_request(app_secret, path, query, body_bytes)

    headers = {"content-type": "application/json"}
    if access_token:
        headers["x-tts-access-token"] = access_token
    return {"url": f"{API_HOST}{path}", "params": query,
            "headers": headers, "body": body_bytes}
