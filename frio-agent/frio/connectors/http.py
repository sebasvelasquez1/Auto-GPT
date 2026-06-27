"""Shared retry/backoff helper.

Hand-rolled (no hard dep) port of the retry loop in Auto-GPT's
``generate_image_with_hf``. Wrap any external call so a transient failure
backs off instead of crashing the flow. ``tenacity``/``httpx`` arrive with the
``http`` extra in later phases; this keeps Phase 0 dependency-light.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    *,
    retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn``; on listed exceptions retry with exponential backoff."""
    attempt = 0
    while True:
        try:
            return fn()
        except exceptions:
            attempt += 1
            if attempt > retries:
                raise
            sleep(min(base_delay * (2 ** (attempt - 1)), max_delay))
