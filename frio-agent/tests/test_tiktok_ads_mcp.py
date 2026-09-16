"""OAuth 2.1 + PKCE builders for the official TikTok Ads MCP server.

Only the deterministic, network-free parts are tested here (PKCE crypto, request/URL
construction) — see tiktok_ads_mcp.py's docstring for why the live discovery/token
calls are intentionally left as NotImplementedError.
"""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import json

from frio.config import Config
from frio.connectors.tiktok_ads_mcp import (
    DiscoveredEndpoints, DiscoveryError, MCP_ENDPOINTS, SCOPE, TikTokAdsMcpAuth,
    build_authorization_url, build_refresh_request, build_registration_request,
    build_token_exchange_request, generate_pkce_pair, generate_state,
)


def test_pkce_pair_meets_rfc7636_shape() -> None:
    pair = generate_pkce_pair()
    assert 43 <= len(pair.verifier) <= 128
    assert pair.method == "S256"
    # challenge must equal base64url(sha256(verifier)), no padding
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(pair.verifier.encode()).digest()).decode().rstrip("=")
    assert pair.challenge == expected
    assert "=" not in pair.verifier and "=" not in pair.challenge


def test_pkce_pairs_are_unique() -> None:
    a, b = generate_pkce_pair(), generate_pkce_pair()
    assert a.verifier != b.verifier
    assert a.challenge != b.challenge


def test_state_is_unique_and_url_safe() -> None:
    s1, s2 = generate_state(), generate_state()
    assert s1 != s2
    assert all(c.isalnum() or c in "-_" for c in s1)


def test_registration_request_is_a_public_client() -> None:
    req = build_registration_request(["https://frio.local/callback"])
    assert req["token_endpoint_auth_method"] == "none"  # no client_secret
    assert "authorization_code" in req["grant_types"]
    assert "refresh_token" in req["grant_types"]
    assert req["scope"] == SCOPE


def test_authorization_url_carries_pkce_and_state() -> None:
    pkce = generate_pkce_pair()
    url = build_authorization_url(
        "https://auth.example/authorize", client_id="cid123",
        redirect_uri="https://frio.local/callback", state="the-state", pkce=pkce)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert qs["response_type"] == ["code"]
    assert qs["client_id"] == ["cid123"]
    assert qs["code_challenge"] == [pkce.challenge]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"] == ["the-state"]
    assert qs["scope"] == [SCOPE]
    # the raw verifier must NEVER appear in the URL (it's PKCE's whole point)
    assert pkce.verifier not in url


def test_token_exchange_request_includes_verifier_not_challenge() -> None:
    req = build_token_exchange_request(
        "https://auth.example/token", client_id="cid123", code="authcode",
        redirect_uri="https://frio.local/callback", code_verifier="the-verifier")
    assert req["data"]["grant_type"] == "authorization_code"
    assert req["data"]["code_verifier"] == "the-verifier"
    assert "client_secret" not in req["data"]  # public client, no secret


def test_refresh_request_shape() -> None:
    req = build_refresh_request("https://auth.example/token", client_id="cid123",
                                refresh_token="rt-abc")
    assert req["data"]["grant_type"] == "refresh_token"
    assert req["data"]["refresh_token"] == "rt-abc"


def test_mcp_endpoints_flat_and_layered() -> None:
    assert "tt-ads-mcp-flat" in MCP_ENDPOINTS["flat"]
    assert "tt-ads-mcp-layer" in MCP_ENDPOINTS["layered"]


def test_available_reflects_stored_token() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    assert auth.available() is False
    auth2 = TikTokAdsMcpAuth(config=Config(tiktok_ads_mcp_access_token="tok"))
    assert auth2.available() is True


def test_start_authorization_prepares_pkce_and_state() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    hint, pkce, state = auth.start_authorization("https://frio.local/callback")
    assert auth._pending_pkce is pkce
    assert auth._pending_state == state
    assert "resource_metadata" in hint  # documents the discovery step, not a guess


def test_exchange_code_requires_prior_authorization_start() -> None:
    import pytest

    auth = TikTokAdsMcpAuth(config=Config())
    with pytest.raises(RuntimeError, match="start_authorization"):
        auth.exchange_code(None, client_id="c", code="x", redirect_uri="r")


# --- discover() / register_client() / exchange_code() / refresh() -----------------
# These verify the RFC 9728/8414/7591 PARSING logic against realistically-shaped fake
# responses (see tiktok_ads_mcp.py's module docstring for why a live call against
# TikTok's real server isn't possible from this environment).

RESOURCE_METADATA_URL = "https://business-api.tiktok.com/.well-known/oauth-protected-resource"
AS_URL = "https://business-api.tiktok.com/portal/oauth"


def _fake_get_sequence(*responses):
    """Returns a callable that yields each response in order, by URL."""
    calls = list(responses)

    def _get(url, headers=None):
        assert calls, f"unexpected extra GET to {url}"
        expected_url, response = calls.pop(0)
        assert url == expected_url, f"expected GET {expected_url}, got {url}"
        return response

    return _get


def test_discover_walks_401_challenge_to_endpoints() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    challenge_header = {"WWW-Authenticate": f'Bearer resource_metadata="{RESOURCE_METADATA_URL}"'}
    resource_meta = json.dumps({"authorization_servers": [AS_URL]}).encode()
    as_meta = json.dumps({
        "authorization_endpoint": f"{AS_URL}/authorize",
        "token_endpoint": f"{AS_URL}/token",
        "registration_endpoint": f"{AS_URL}/register",
    }).encode()
    fake_get = _fake_get_sequence(
        (auth.mcp_url(), (401, challenge_header, b"")),
        (RESOURCE_METADATA_URL, (200, {}, resource_meta)),
        (f"{AS_URL}/.well-known/oauth-authorization-server", (200, {}, as_meta)),
    )
    discovered = auth.discover(http_get=fake_get)
    assert discovered.authorization_endpoint == f"{AS_URL}/authorize"
    assert discovered.token_endpoint == f"{AS_URL}/token"
    assert discovered.registration_endpoint == f"{AS_URL}/register"


def test_discover_raises_clearly_on_unexpected_status() -> None:
    import pytest

    auth = TikTokAdsMcpAuth(config=Config())
    fake_get = lambda url, headers=None: (200, {}, b"")  # no 401 challenge
    with pytest.raises(DiscoveryError, match="expected HTTP 401"):
        auth.discover(http_get=fake_get)


def test_discover_raises_on_missing_resource_metadata_header() -> None:
    import pytest

    auth = TikTokAdsMcpAuth(config=Config())
    fake_get = lambda url, headers=None: (401, {"WWW-Authenticate": "Bearer"}, b"")
    with pytest.raises(DiscoveryError, match="no resource_metadata"):
        auth.discover(http_get=fake_get)


def test_register_client_stores_client_id_in_config() -> None:
    discovered = DiscoveredEndpoints(
        authorization_endpoint=f"{AS_URL}/authorize", token_endpoint=f"{AS_URL}/token",
        registration_endpoint=f"{AS_URL}/register")
    cfg = Config()
    auth = TikTokAdsMcpAuth(config=cfg)
    fake_post = lambda url, payload, headers=None: (
        201, {}, json.dumps({"client_id": "new-client-123"}).encode())
    client_id = auth.register_client(discovered, ["https://frio.local/callback"],
                                     http_post=fake_post)
    assert client_id == "new-client-123"
    assert cfg.tiktok_ads_mcp_client_id == "new-client-123"


def test_register_client_requires_registration_endpoint() -> None:
    import pytest

    discovered = DiscoveredEndpoints(
        authorization_endpoint="x", token_endpoint="y", registration_endpoint=None)
    auth = TikTokAdsMcpAuth(config=Config())
    with pytest.raises(DiscoveryError, match="registration_endpoint"):
        auth.register_client(discovered, ["https://frio.local/callback"])


def test_exchange_code_stores_tokens_in_config() -> None:
    discovered = DiscoveredEndpoints(
        authorization_endpoint=f"{AS_URL}/authorize", token_endpoint=f"{AS_URL}/token")
    cfg = Config()
    auth = TikTokAdsMcpAuth(config=cfg)
    auth.start_authorization("https://frio.local/callback")
    fake_post = lambda url, data, headers=None: (
        200, {}, json.dumps({"access_token": "at-1", "refresh_token": "rt-1"}).encode())
    tokens = auth.exchange_code(discovered, client_id="cid", code="authcode",
                                redirect_uri="https://frio.local/callback",
                                http_post=fake_post)
    assert tokens["access_token"] == "at-1"
    assert cfg.tiktok_ads_mcp_access_token == "at-1"
    assert cfg.tiktok_ads_mcp_refresh_token == "rt-1"
    assert auth.available() is True


def test_refresh_requires_stored_refresh_token() -> None:
    import pytest

    discovered = DiscoveredEndpoints(authorization_endpoint="x", token_endpoint="y")
    auth = TikTokAdsMcpAuth(config=Config())
    with pytest.raises(RuntimeError, match="no refresh_token stored"):
        auth.refresh(discovered)


def test_refresh_updates_access_token() -> None:
    discovered = DiscoveredEndpoints(authorization_endpoint="x", token_endpoint=f"{AS_URL}/token")
    cfg = Config(tiktok_ads_mcp_client_id="cid", tiktok_ads_mcp_refresh_token="rt-1")
    auth = TikTokAdsMcpAuth(config=cfg)
    fake_post = lambda url, data, headers=None: (
        200, {}, json.dumps({"access_token": "at-2"}).encode())
    tokens = auth.refresh(discovered, http_post=fake_post)
    assert tokens["access_token"] == "at-2"
    assert cfg.tiktok_ads_mcp_access_token == "at-2"


def test_run_request_wraps_connection_failure_in_discovery_error() -> None:
    """Real bug found by actually running this against a blocked proxy: urllib's
    URLError (connection-level failure, no HTTP response at all) must become a clear
    DiscoveryError, not leak a raw traceback to the CLI user."""
    import pytest
    import urllib.error

    from frio.connectors.tiktok_ads_mcp import _run_request

    class _FakeRequest:
        full_url = "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat"

    def _boom(*a, **kw):
        raise urllib.error.URLError("Tunnel connection failed: 403 Forbidden")

    import frio.connectors.tiktok_ads_mcp as mod
    original = mod.urllib.request.urlopen
    mod.urllib.request.urlopen = _boom
    try:
        with pytest.raises(DiscoveryError, match="could not reach"):
            _run_request(_FakeRequest())
    finally:
        mod.urllib.request.urlopen = original
