"""LLM layer — Claude via the Anthropic SDK, with an offline contract.

The strategist calls Claude when a key + SDK are present, and falls back to
deterministic heuristics otherwise so the pipeline always runs.
"""
