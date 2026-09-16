"""OAuth 2.1 + PKCE flow for the official TikTok Ads MCP server.

Network-free tests: PKCE crypto, request/URL construction, and the discovery/token
parsing logic against realistically-shaped fake responses. Discovery and dynamic
client registration have ALSO been run for real against TikTok (2026-09-16); two
regression tests here pin the two deviations that live run exposed (POST-only OAuth
challenge, OIDC-style metadata URL) so they cannot silently come back.
"""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import json

import pytest

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
        (RESOURCE_METADATA_URL, (200, {}, resource_meta)),
        (f"{AS_URL}/.well-known/oauth-authorization-server", (200, {}, as_meta)),
    )
    fake_probe = lambda url: (401, challenge_header, b"unauthorized")
    discovered = auth.discover(http_get=fake_get, http_probe=fake_probe)
    assert discovered.authorization_endpoint == f"{AS_URL}/authorize"
    assert discovered.token_endpoint == f"{AS_URL}/token"
    assert discovered.registration_endpoint == f"{AS_URL}/register"


def test_discover_raises_clearly_on_unexpected_status() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    fake_probe = lambda url: (200, {}, b"")  # no 401 challenge
    with pytest.raises(DiscoveryError, match="expected HTTP 401"):
        auth.discover(http_probe=fake_probe)


def test_discover_raises_on_missing_resource_metadata_header() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    fake_probe = lambda url: (401, {"WWW-Authenticate": "Bearer"}, b"")
    with pytest.raises(DiscoveryError, match="no resource_metadata"):
        auth.discover(http_probe=fake_probe)


def test_discover_probes_with_post_not_get() -> None:
    """Regression test for the bug the first LIVE run hit (2026-09-16): TikTok's MCP
    endpoint answers the OAuth challenge only to a POST. A GET gets a bare
    "405 Method Not Allowed" with NO WWW-Authenticate header, so a GET-based probe
    can never discover anything. Asserts the shipped default probe uses POST."""
    import urllib.request

    from frio.connectors.tiktok_ads_mcp import _http_probe_challenge


    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["method"] = req.get_method()
        seen["accept"] = req.get_header("Accept")
        raise AssertionError("stop before the network")

    original = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        with pytest.raises(AssertionError, match="stop before the network"):
            _http_probe_challenge("https://business-api.tiktok.com/open_mcp/x")
    finally:
        urllib.request.urlopen = original
    assert seen["method"] == "POST"
    assert "text/event-stream" in seen["accept"]


def test_discover_reports_405_body_when_challenge_is_refused() -> None:
    """The live failure mode, verbatim: the error has to name the real status and
    body so the next person sees what TikTok actually said."""
    auth = TikTokAdsMcpAuth(config=Config())
    fake_probe = lambda url: (405, {}, b"Method Not Allowed")
    with pytest.raises(DiscoveryError) as exc:
        auth.discover(http_probe=fake_probe)
    assert "405" in str(exc.value)
    assert "Method Not Allowed" in str(exc.value)


def test_as_metadata_urls_try_append_form_first_then_rfc8414() -> None:
    """TikTok serves the OIDC-style append form and 404s the RFC 8414 insert form
    (both probed live, 2026-09-16), so append must be tried first — but the RFC form
    stays as a fallback so a spec-compliant server also works."""
    from frio.connectors.tiktok_ads_mcp import _as_metadata_urls

    urls = _as_metadata_urls("https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat/oauth")
    assert urls == [
        "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat/oauth"
        "/.well-known/oauth-authorization-server",
        "https://business-api.tiktok.com/.well-known/oauth-authorization-server"
        "/open_mcp/tt-ads-mcp-flat/oauth",
    ]


def test_discover_falls_back_to_rfc8414_url_when_append_form_404s() -> None:
    auth = TikTokAdsMcpAuth(config=Config())
    challenge_header = {"WWW-Authenticate": f'Bearer resource_metadata="{RESOURCE_METADATA_URL}"'}
    resource_meta = json.dumps({"authorization_servers": [AS_URL]}).encode()
    as_meta = json.dumps({"authorization_endpoint": f"{AS_URL}/authorize",
                          "token_endpoint": f"{AS_URL}/token"}).encode()
    rfc8414_url = ("https://business-api.tiktok.com/.well-known/"
                   "oauth-authorization-server/portal/oauth")
    fake_get = _fake_get_sequence(
        (RESOURCE_METADATA_URL, (200, {}, resource_meta)),
        (f"{AS_URL}/.well-known/oauth-authorization-server", (404, {}, b"not found")),
        (rfc8414_url, (200, {}, as_meta)),
    )
    discovered = auth.discover(http_get=fake_get, http_probe=lambda url: (401, challenge_header, b""))
    assert discovered.token_endpoint == f"{AS_URL}/token"


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


# --- Pending-authorization handoff (human-in-the-middle between the two commands) ---

def test_parse_redirect_url_extracts_code_and_state() -> None:
    from frio.connectors.tiktok_ads_mcp import parse_redirect_url

    code, state = parse_redirect_url(
        "  https://frio.local/callback?code=abc123&state=xyz789  ")
    assert (code, state) == ("abc123", "xyz789")


def test_parse_redirect_url_surfaces_tiktok_error_instead_of_missing_code() -> None:
    from frio.connectors.tiktok_ads_mcp import PendingAuthError, parse_redirect_url

    with pytest.raises(PendingAuthError, match="access_denied.*user refused"):
        parse_redirect_url("https://frio.local/callback?error=access_denied"
                           "&error_description=user+refused")


def test_parse_redirect_url_rejects_a_url_with_no_code() -> None:
    from frio.connectors.tiktok_ads_mcp import PendingAuthError, parse_redirect_url

    with pytest.raises(PendingAuthError, match="no 'code' parameter"):
        parse_redirect_url("https://frio.local/callback")


def test_verify_state_rejects_mismatch_and_missing_state() -> None:
    """The CSRF guard is the whole point of state — a missing one must NOT pass."""
    from frio.connectors.tiktok_ads_mcp import PendingAuthError, verify_state

    verify_state("s", "s")  # matching state is accepted
    with pytest.raises(PendingAuthError, match="state mismatch"):
        verify_state("other", "s")
    with pytest.raises(PendingAuthError, match="state mismatch"):
        verify_state(None, "s")


def test_pending_auth_round_trips_and_is_owner_only(tmp_path) -> None:
    """It holds a PKCE verifier (a secret), so the file must not be world-readable."""
    import stat

    from frio.connectors.tiktok_ads_mcp import load_pending_auth, save_pending_auth

    target = tmp_path / "pending.json"
    data = {"client_id": "cid", "verifier": "v", "state": "s",
            "redirect_uri": "https://frio.local/callback", "endpoint": "flat"}
    save_pending_auth(data, path=str(target))
    assert load_pending_auth(path=str(target)) == data
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_load_pending_auth_explains_itself_when_absent_or_incomplete(tmp_path) -> None:
    from frio.connectors.tiktok_ads_mcp import (
        PendingAuthError, load_pending_auth, save_pending_auth,
    )

    with pytest.raises(PendingAuthError, match="run `frio ads mcp-authorize` first"):
        load_pending_auth(path=str(tmp_path / "nope.json"))

    partial = tmp_path / "partial.json"
    save_pending_auth({"client_id": "cid"}, path=str(partial))
    with pytest.raises(PendingAuthError, match="missing verifier, state, redirect_uri"):
        load_pending_auth(path=str(partial))
