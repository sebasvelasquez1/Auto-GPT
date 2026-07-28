"""TikTok Shop request signing — pinned to PUBLISHED test vectors.

These are not self-consistent tests (which would only prove the code agrees with
itself). Both expected digests come from independent published sources and were
reproduced before this module was written:
  - Vector 1: TikTok's own "Sign your API request" doc worked example.
  - Vector 2: the EcomPHP/tiktokshop-php SDK unit test (de-facto PHP SDK).
If a refactor ever breaks these, the signature is wrong — not the test.
"""

from __future__ import annotations

import json

from frio.connectors.tiktok_sign import API_HOST, prepare_call, sign_request

# Vector 1 — official TikTok doc worked example.
V1_SECRET = "e59af819cc"
V1_PATH = "/authorization/202309/shops"
V1_PARAMS = {"app_key": "29a39d", "timestamp": "1623812664"}
V1_EXPECTED = "b596b73e0cc6de07ac26f036364178ab16b0a907af13d43f0a0cd2345f582dc8"

# Vector 2 — EcomPHP/tiktokshop-php unit test (exercises the body path).
V2_SECRET = "app_secret"
V2_PATH = "/test-api"
V2_PARAMS = {"foo": "bar"}
V2_EXPECTED = "d3cb7fe11ecae942802ceeca67e7cf10120cc12f1517d45fbc1c8cfe5413c80f"


def test_official_doc_vector() -> None:
    assert sign_request(V1_SECRET, V1_PATH, V1_PARAMS) == V1_EXPECTED


def test_ecomphp_sdk_vector() -> None:
    assert sign_request(V2_SECRET, V2_PATH, V2_PARAMS) == V2_EXPECTED


def test_sign_and_access_token_are_excluded() -> None:
    """Both must be dropped before signing — including them is a classic 401 cause."""
    noisy = dict(V1_PARAMS, sign="stale-value", access_token="TTP_secret")
    assert sign_request(V1_SECRET, V1_PATH, noisy) == V1_EXPECTED


def test_param_order_does_not_matter() -> None:
    reversed_params = {"timestamp": "1623812664", "app_key": "29a39d"}
    assert sign_request(V1_SECRET, V1_PATH, reversed_params) == V1_EXPECTED


def test_multipart_body_is_not_signed() -> None:
    body = b'{"x":1}'
    with_json = sign_request(V2_SECRET, V2_PATH, V2_PARAMS, body, "application/json")
    with_multipart = sign_request(V2_SECRET, V2_PATH, V2_PARAMS, body,
                                  "multipart/form-data; boundary=abc")
    assert with_json != with_multipart
    assert with_multipart == V2_EXPECTED  # body excluded -> same as the no-body vector


def test_prepare_call_signs_the_exact_bytes_it_returns() -> None:
    """The returned bytes MUST be what was signed — re-serializing breaks the sign."""
    call = prepare_call("29a39d", V1_SECRET, "/product/202309/products/search",
                        access_token="TTP_tok", shop_cipher="CIPHER",
                        body={"page_size": 50}, timestamp=1623812664)
    recomputed = sign_request(V1_SECRET, "/product/202309/products/search",
                              call["params"], call["body"])
    assert recomputed == call["params"]["sign"]
    assert json.loads(call["body"]) == {"page_size": 50}


def test_prepare_call_wiring() -> None:
    call = prepare_call("29a39d", V1_SECRET, V1_PATH, access_token="TTP_tok",
                        timestamp=1623812664)
    assert call["url"] == f"{API_HOST}{V1_PATH}"
    assert call["headers"]["x-tts-access-token"] == "TTP_tok"
    assert call["headers"]["content-type"] == "application/json"
    assert call["params"]["sign"] == V1_EXPECTED  # no body, no cipher -> vector 1
