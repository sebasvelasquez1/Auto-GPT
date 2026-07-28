"""Frío — autonomous TikTok-Shop POD/Dropshipping agent.

A standalone, Claude-centric, MCP-friendly engine. The shared core
(competitor discovery -> ad research -> strategist -> creation -> test ->
optimize -> ads) serves two swappable pipelines (POD and Dropshipping) behind
common ProductOrigin/Fulfillment interfaces.

Phase 0 = skeleton: config, capability registry with gating, DB models,
pipeline interfaces, CLI. Live/gated capabilities stay disabled until config
flips them on.
"""

__version__ = "0.0.1"
