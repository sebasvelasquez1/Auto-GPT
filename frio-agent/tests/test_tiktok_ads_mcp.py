"""OAuth 2.1 + PKCE builders for the official TikTok Ads MCP server.

Only the deterministic, network-free parts are tested here (PKCE crypto, request/URL
construction) — see tiktok_ads_mcp.py's docstring for why the live discovery/token
calls are intentionally left as NotImplementedError.
"""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from frio.config import Config
from frio.connectors.tiktok_ads_mcp import (
    MCP_ENDPOINTS, SCOPE, TikTokAdsMcpAuth, build_authorization_url,
    build_refresh_request, build_registration_request, build_token_exchange_request,
    generate_pkce_pair, generate_state,
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
