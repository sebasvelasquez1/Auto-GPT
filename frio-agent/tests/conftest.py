"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_engine_cache():
    """Clear the per-URL engine cache after each test.

    The cache (frio.db.base._ENGINES) shares one in-memory DB per URL across calls,
    which is correct at runtime but would otherwise leak state between tests that use
    "sqlite://". Clearing after each test keeps tests isolated and order-independent.
    """
    yield
    from frio.db.base import _ENGINES

    for engine in _ENGINES.values():
        try:
            engine.dispose()
        except Exception:
            pass
    _ENGINES.clear()
