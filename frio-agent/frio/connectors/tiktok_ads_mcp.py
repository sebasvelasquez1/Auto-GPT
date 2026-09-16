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

What's fully built and tested here (pure, deterministic, no network): PKCE generation,
the dynamic-client-registration request body, the authorization URL, and the token
request bodies. What still needs a live network call (network access to TikTok's real
server was not available while building this) is the actual HTTP round-trip: fetching
the two metadata documents, POSTing registration, and exchanging the code — each is
marked ``NotImplementedError`` below with the exact next step, same convention as every
other not-yet-live connector in this codebase (see tiktok_shop_catalog.py).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

from ..config import Config

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

    def discover(self) -> DiscoveredEndpoints:
        """RFC 9728 + RFC 8414 discovery: fetch the 401 challenge's resource_metadata,
        then the authorization server's own metadata document.

        NOT IMPLEMENTED: requires a live HTTP round-trip to business-api.tiktok.com,
        which was not reachable while building this (see the module docstring). Wire
        with: GET self.mcp_url() -> read WWW-Authenticate's resource_metadata URL ->
        GET that JSON -> read authorization_servers[0] -> GET
        f"{that}/.well-known/oauth-authorization-server" -> return the 3 endpoints.
        """
        raise NotImplementedError(
            "wire the RFC 9728/8414 discovery HTTP calls here — see docstring")

    def register_client(self, discovered: DiscoveredEndpoints,
                        redirect_uris: list[str]) -> str:
        """POST build_registration_request(...) to discovered.registration_endpoint.
        NOT IMPLEMENTED: needs live network. Returns the resulting client_id."""
        raise NotImplementedError("wire dynamic client registration POST here")

    def exchange_code(self, discovered: DiscoveredEndpoints, *, client_id: str,
                      code: str, redirect_uri: str) -> dict:
        """POST build_token_exchange_request(...); on success, persist access_token +
        refresh_token (+ expiry) into config/storage. NOT IMPLEMENTED: live network."""
        if self._pending_pkce is None:
            raise RuntimeError("call start_authorization() first")
        raise NotImplementedError("wire the token-exchange POST here")

    def refresh(self, discovered: DiscoveredEndpoints) -> dict:
        """POST build_refresh_request(...). NOT IMPLEMENTED: live network."""
        raise NotImplementedError("wire the refresh POST here")
