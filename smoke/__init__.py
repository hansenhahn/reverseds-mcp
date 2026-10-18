"""Smoke-test harness for re-mcp + melonDS.

Deterministic, local integration tests: boot melonDS headless, drive the real
MCP server (from source, over stdio) and assert on tool responses. No Docker.
"""
