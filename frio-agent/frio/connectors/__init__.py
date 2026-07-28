"""External-API connectors (the MCP/connector boundary).

Each connector follows the dispatch + retry/backoff pattern borrowed from
Auto-GPT's autogpt/commands/image_gen.py: read keys from Config, call the
external API, retry with exponential backoff.
"""
