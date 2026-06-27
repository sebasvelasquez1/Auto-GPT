"""LLM client abstraction.

``LLMClient.complete_json`` returns a parsed dict (the strategist prompts always
ask for JSON). ``AnthropicClient`` uses the Anthropic SDK when available; if the
key or SDK is missing it reports ``available() == False`` and the strategist
uses heuristics instead.

Model note: confirm the current model id/pricing via the claude-api skill rather
than hardcoding from memory; the default below is a placeholder that can be
overridden by ``FRIO_CLAUDE_MODEL``.
"""

from __future__ import annotations

import json
import os
from typing import Protocol, runtime_checkable

from ..config import Config


@runtime_checkable
class LLMClient(Protocol):
    def available(self) -> bool: ...

    def complete_json(self, system: str, prompt: str) -> dict: ...


class AnthropicClient:
    def __init__(self, config: Config) -> None:
        self._key = config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = os.getenv("FRIO_CLAUDE_MODEL", "claude-sonnet-4-6")
        self._client = None
        if self._key:
            try:  # SDK is an optional ([llm]) dependency
                import anthropic  # type: ignore

                self._client = anthropic.Anthropic(api_key=self._key)
            except Exception:
                self._client = None

    def available(self) -> bool:
        return self._client is not None

    def complete_json(self, system: str, prompt: str) -> dict:
        if not self.available():
            return {}
        msg = self._client.messages.create(  # type: ignore[union-attr]
            model=self._model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content).strip()
        try:
            return json.loads(_strip_fences(text))
        except json.JSONDecodeError:
            return {}


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()


def make_llm(config: Config) -> LLMClient:
    return AnthropicClient(config)
