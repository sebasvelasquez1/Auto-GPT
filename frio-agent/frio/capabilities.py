"""Capability registry with gating.

Ports the useful idea from Auto-GPT's ``@command`` decorator
(autogpt/command_decorator.py): a capability declares ``enabled`` as either a
bool or ``Callable[[Config], bool]`` plus a ``disabled_reason``. This is exactly
the mechanism Frío needs for gated/HITL tools — a capability like
``ads.place_order`` registers as
``enabled=lambda c: c.ads_live_enabled and c.seller_approved`` and simply does
not become available until config flips it on.

The LLM may *propose* any capability; only deterministic code + a human may
*authorize* gated (spend/commerce) ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Config

EnabledType = bool | Callable[[Config], bool]


@dataclass
class Capability:
    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: EnabledType = True
    disabled_reason: str | None = None
    # Coarse category for display/policy. "gated" => requires config + HITL.
    category: str = "core"

    def is_enabled(self, config: Config) -> bool:
        if callable(self.enabled):
            return bool(self.enabled(config))
        return bool(self.enabled)


class CapabilityRegistry:
    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}

    def register(self, cap: Capability) -> None:
        if cap.name in self._caps:
            raise ValueError(f"duplicate capability: {cap.name}")
        self._caps[cap.name] = cap

    def get(self, name: str) -> Capability:
        return self._caps[name]

    def all(self) -> list[Capability]:
        return sorted(self._caps.values(), key=lambda c: c.name)

    def enabled(self, config: Config) -> list[Capability]:
        return [c for c in self.all() if c.is_enabled(config)]


REGISTRY = CapabilityRegistry()


def capability(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    *,
    enabled: EnabledType = True,
    disabled_reason: str | None = None,
    category: str = "core",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function as a Frío capability."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cap = Capability(
            name=name,
            description=description,
            func=func,
            parameters=parameters or {},
            enabled=enabled,
            disabled_reason=disabled_reason,
            category=category,
        )
        REGISTRY.register(cap)
        func.capability = cap  # type: ignore[attr-defined]
        return func

    return decorator


def load_all_capabilities() -> None:
    """Import module side-effects so capabilities self-register."""
    from . import compliance  # noqa: F401
    from .modules import (  # noqa: F401
        ads, analyzer, commerce, competitors, creation, optimize, product_pod, strategist,
    )
