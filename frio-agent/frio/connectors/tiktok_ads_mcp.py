"""OAuth 2.1 + PKCE for the official TikTok for Business MCP server.

Why this connector exists: research (2026-09-15) found the official MCP server
requires NO developer account and NO registered app — the single lowest-friction
path for a seller without a registered company. See
knowledge/investigacion/2026-09-conexion-tiktok-shop-ads-consolidado.md §5.

Confirmed (third-party live-probe ledger, api-evangelist/tiktok-ads, 2026-08-13 /
re-probed 2026-09-11 — NOT read from TikTok's own docs, which were unreachable):
  - Endpoints: business-api.tiktok.com/open_mcp/tt-ads-mcp-flat (~400 tools) and
    .../tt-ads-mcp-layer (~40 tools, progressive disclosure).
  - Auth: OAuth 2.1, authorization-code + PKCE (S256 required), dynamic client
    registration (RFC 7591), scope "mcp:tt4b", token_endpoint_auth_methods: none
    (public client — no client_secret, consistent with "no developer app needed").
  - Both endpoints answered HTTP 401 with a
    ``WWW-Authenticate: Bearer resource_metadata="..."`` challenge — i.e. the server
    itself advertises RFC 9728 Protected Resource Metadata.
  - Grant lifetime: 30 days, then reauthorize.

DELIBERATE DESIGN CHOICE — do not hardcode TikTok's endpoint paths as ground truth.
The third-party probe found specific paths (``/portal/mcp-tt4b-authorize`` etc.), but
those were observed, not read from TikTok's own documentation, and RFC 9728 exists
precisely so a client does NOT need to hardcode them: the 401 challenge's
``resource_metadata`` URL points to a JSON document naming the real
``authorization_servers``, and that server's own ``/.well-known/oauth-authorization-
server`` (RFC 8414) names the real ``authorization_endpoint``, ``token_endpoint`` and
``registration_endpoint``. This module implements that DISCOVERY flow instead of
guessing paths — it is protocol-correct regardless of what TikTok's current paths are,
and matches the "no inventar" project rule better than repeating a third-party guess.

Status (2026-09-16): the FULL flow is implemented — PKCE, dynamic client registration,
RFC 9728/8414 discovery, code exchange, and refresh. The request-building and
response-parsing logic is unit-tested against realistically-shaped fake HTTP responses
(tests/test_tiktok_ads_mcp.py). What is NOT yet verified is a live round-trip against
TikTok's real server: this environment's egress proxy blocks business-api.tiktok.com
outright (confirmed via direct curl -> "policy denial", not a flaky failure — see
knowledge/investigacion/). Every network call below takes an injectable http_get/
http_post so it can be run for real from a network that can reach TikTok (e.g. the
user's own machine) via ``frio ads mcp-authorize`` — if TikTok's real response shape
ever differs from the RFCs, the code raises ``DiscoveryError`` with the actual body
rather than silently misparsing.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlencode

from ..config import Config

# Injectable so tests can verify the parsing logic against fake responses without a
# live network call — this environment's egress proxy blocks business-api.tiktok.com
# outright (confirmed via direct curl, "policy denial", not a flaky failure), so the
# request/response PARSING is what's actually verified here; the live round-trip
# needs to run from a network that can reach TikTok (e.g. the user's own machine).
HttpResponse = tuple[int, dict, bytes]


def _run_request(req: urllib.request.Request) -> HttpResponse:
    """Shared error handling. urllib raises HTTPError for a real HTTP error response
    (fine — we want the body TikTok sent back) but raises the more generic URLError
    for a connection-level failure (DNS, refused, proxy block) — that one has no HTTP
    status or body to parse, so it must become a clear DiscoveryError, not a crash.
    Confirmed necessary by actually running this against a blocked proxy: it raised a
    raw ``URLError`` traceback instead of a usable message before this fix.
    """
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()
    except urllib.error.URLError as exc:
        raise DiscoveryError(
            f"could not reach {req.full_url} ({exc.reason}) — run this from a network "
            f"that can reach TikTok's servers") from exc


def _http_get(url: str, headers: dict | None = None) -> HttpResponse:
    return _run_request(urllib.request.Request(url, headers=headers or {}, method="GET"))


def _http_post_json(url: str, payload: dict, headers: dict | None = None) -> HttpResponse:
    body = json.dumps(payload).encode()
    return _run_request(urllib.request.Request(
        url, data=body, method="POST",
        headers={**(headers or {}), "Content-Type": "application/json"}))


def _http_post_form(url: str, data: dict, headers: dict | None = None) -> HttpResponse:
    body = urlencode(data).encode()
    return _run_request(urllib.request.Request(
        url, data=body, method="POST",
        headers={**(headers or {}), "Content-Type": "application/x-www-form-urlencoded"}))


class DiscoveryError(RuntimeError):
    """The MCP server's response didn't match the expected RFC 9728/8414 shape."""

MCP_ENDPOINTS = {
    "flat": "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat",
    "layered": "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-layer",
}
SCOPE = "mcp:tt4b"


@dataclass
class PkcePair:
    verifier: str
    challenge: str
    method: str = "S256"


def generate_pkce_pair() -> PkcePair:
    """RFC 7636 S256 PKCE pair. 43-128 char verifier; challenge = base64url(sha256())."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return PkcePair(verifier=verifier, challenge=challenge)


def generate_state() -> str:
    """CSRF token for the authorization request — verify it matches on callback."""
    return secrets.token_urlsafe(24)


@dataclass
class DiscoveredEndpoints:
    """What RFC 9728 + RFC 8414 discovery is supposed to yield. Populate this from a
    real fetch (see ``discover`` below) — never hardcode these as constants."""
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None


def build_registration_request(redirect_uris: list[str], *,
                               client_name: str = "Frio Agent") -> dict:
    """RFC 7591 dynamic client registration request body (public client: no secret)."""
    return {
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # public client — confirmed by the probe
        "scope": SCOPE,
    }


def build_authorization_url(authorization_endpoint: str, *, client_id: str,
                            redirect_uri: str, state: str, pkce: PkcePair) -> str:
    """The URL to hand the seller — they open it, log into TikTok, approve, and land
    back on ``redirect_uri`` with ``?code=...&state=...``."""
    params = {
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
        "scope": SCOPE, "state": state,
        "code_challenge": pkce.challenge, "code_challenge_method": pkce.method,
    }
    return f"{authorization_endpoint}?{urlencode(params)}"


def build_token_exchange_request(token_endpoint: str, *, client_id: str, code: str,
                                 redirect_uri: str, code_verifier: str) -> dict:
    """POST body to exchange an auth code for tokens. No client_secret (public client)."""
    return {"url": token_endpoint,
            "data": {"grant_type": "authorization_code", "client_id": client_id,
                     "code": code, "redirect_uri": redirect_uri,
                     "code_verifier": code_verifier}}


def build_refresh_request(token_endpoint: str, *, client_id: str,
                          refresh_token: str) -> dict:
    return {"url": token_endpoint,
            "data": {"grant_type": "refresh_token", "client_id": client_id,
                     "refresh_token": refresh_token}}


@dataclass
class TikTokAdsMcpAuth:
    """Auth state for one MCP endpoint. ``available()`` reflects whether we hold a
    live-looking token — it does NOT verify the token still works (that needs a call).
    """
    config: Config
    endpoint: str = "flat"  # "flat" (~400 tools) or "layered" (~40 tools)
    _pending_pkce: PkcePair | None = field(default=None, repr=False)
    _pending_state: str | None = field(default=None, repr=False)

    def mcp_url(self) -> str:
        return MCP_ENDPOINTS[self.endpoint]

    def available(self) -> bool:
        return bool(self.config.tiktok_ads_mcp_access_token)

    def start_authorization(self, redirect_uri: str) -> tuple[str, PkcePair, str]:
        """Step the seller needs: returns (discovery_hint, pkce, state).

        The real authorization URL cannot be built until discovery (below) has run
        against a live network, because ``authorization_endpoint`` is not something we
        hardcode. This method prepares and holds the PKCE/state the caller will need
        once discovery supplies the endpoint.
        """
        self._pending_pkce = generate_pkce_pair()
        self._pending_state = generate_state()
        return (f"{self.mcp_url()} (401 challenge -> resource_metadata -> "
                f"authorization_servers -> /.well-known/oauth-authorization-server)",
                self._pending_pkce, self._pending_state)

    def discover(self, *, http_get=_http_get) -> DiscoveredEndpoints:
        """RFC 9728 + RFC 8414 discovery: fetch the 401 challenge's resource_metadata,
        then the authorization server's own metadata document.

        Live-network status: written and unit-tested against mocked responses shaped
        exactly like the RFCs specify, but NEVER exercised against the real TikTok
        server — this environment's egress proxy blocks business-api.tiktok.com
        outright (confirmed via direct curl: "policy denial", not a flaky failure).
        Run this from a network that can actually reach TikTok (your own machine) for
        the first real test; if TikTok's real response shape differs from the RFCs,
        this will raise ``DiscoveryError`` with the actual body, not silently misparse.
        """
        status, headers, _ = http_get(self.mcp_url())
        if status != 401:
            raise DiscoveryError(
                f"expected HTTP 401 (OAuth challenge) from {self.mcp_url()}, got {status}")
        challenge = headers.get("WWW-Authenticate") or headers.get("www-authenticate")
        match = re.search(r'resource_metadata="([^"]+)"', challenge or "")
        if not match:
            raise DiscoveryError(
                f"no resource_metadata in WWW-Authenticate header: {challenge!r}")
        rs_status, _, rs_body = http_get(match.group(1))
        if rs_status != 200:
            raise DiscoveryError(f"resource metadata fetch failed: HTTP {rs_status}")
        resource_meta = json.loads(rs_body)
        servers = resource_meta.get("authorization_servers") or []
        if not servers:
            raise DiscoveryError(f"no authorization_servers in {resource_meta!r}")
        as_status, _, as_body = http_get(
            f"{servers[0].rstrip('/')}/.well-known/oauth-authorization-server")
        if as_status != 200:
            raise DiscoveryError(f"authorization server metadata fetch failed: HTTP {as_status}")
        as_meta = json.loads(as_body)
        try:
            return DiscoveredEndpoints(
                authorization_endpoint=as_meta["authorization_endpoint"],
                token_endpoint=as_meta["token_endpoint"],
                registration_endpoint=as_meta.get("registration_endpoint"))
        except KeyError as exc:
            raise DiscoveryError(f"missing {exc} in authorization server metadata") from exc

    def register_client(self, discovered: DiscoveredEndpoints,
                        redirect_uris: list[str], *, http_post=_http_post_json) -> str:
        """POST build_registration_request(...) to discovered.registration_endpoint,
        per RFC 7591. Same live-network caveat as ``discover`` above."""
        if not discovered.registration_endpoint:
            raise DiscoveryError("authorization server did not advertise a "
                                 "registration_endpoint (RFC 7591)")
        req = build_registration_request(redirect_uris)
        status, _, body = http_post(discovered.registration_endpoint, req)
        if status not in (200, 201):
            raise DiscoveryError(f"client registration failed: HTTP {status} {body!r}")
        parsed = json.loads(body)
        if "client_id" not in parsed:
            raise DiscoveryError(f"registration response missing client_id: {parsed!r}")
        self.config.tiktok_ads_mcp_client_id = parsed["client_id"]
        return parsed["client_id"]

    def exchange_code(self, discovered: DiscoveredEndpoints, *, client_id: str,
                      code: str, redirect_uri: str, http_post=_http_post_form) -> dict:
        """Exchange the authorization code for tokens. Requires
        ``start_authorization()`` to have run first (needs the PKCE verifier)."""
        if self._pending_pkce is None:
            raise RuntimeError("call start_authorization() first")
        req = build_token_exchange_request(
            discovered.token_endpoint, client_id=client_id, code=code,
            redirect_uri=redirect_uri, code_verifier=self._pending_pkce.verifier)
        status, _, body = http_post(req["url"], req["data"])
        if status != 200:
            raise DiscoveryError(f"token exchange failed: HTTP {status} {body!r}")
        tokens = json.loads(body)
        if "access_token" not in tokens:
            raise DiscoveryError(f"token response missing access_token: {tokens!r}")
        self.config.tiktok_ads_mcp_access_token = tokens["access_token"]
        if "refresh_token" in tokens:
            self.config.tiktok_ads_mcp_refresh_token = tokens["refresh_token"]
        return tokens

    def refresh(self, discovered: DiscoveredEndpoints, *, http_post=_http_post_form) -> dict:
        """Refresh the access token using the stored refresh_token."""
        if not self.config.tiktok_ads_mcp_refresh_token:
            raise RuntimeError("no refresh_token stored — run exchange_code() first")
        client_id = self.config.tiktok_ads_mcp_client_id
        if not client_id:
            raise RuntimeError("no client_id stored — run register_client() first")
        req = build_refresh_request(discovered.token_endpoint, client_id=client_id,
                                    refresh_token=self.config.tiktok_ads_mcp_refresh_token)
        status, _, body = http_post(req["url"], req["data"])
        if status != 200:
            raise DiscoveryError(f"token refresh failed: HTTP {status} {body!r}")
        tokens = json.loads(body)
        self.config.tiktok_ads_mcp_access_token = tokens["access_token"]
        if "refresh_token" in tokens:
            self.config.tiktok_ads_mcp_refresh_token = tokens["refresh_token"]
        return tokens
