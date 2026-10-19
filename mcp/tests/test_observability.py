"""Observability tests: capture-empty error and logging level."""
import logging

import pytest

import re_mcp.tools.control as control
from re_mcp.logging_setup import level_from_env


def test_screen_capture_empty_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A capture that decodes 0 frames returns error + hint, not empty paths."""
    monkeypatch.setattr(
        control, "control_call", lambda *a, **k: {"binary": {"width": 256, "height": 192, "data": b""}}
    )
    monkeypatch.setattr(control, "save_framebuffer_pngs", lambda *a, **k: {"paths": []})
    out = control.screen_capture()
    assert "error" in out and "hint" in out
    assert "paths" not in out


def test_screen_capture_ok_returns_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """A capture with a frame returns the saved paths."""
    monkeypatch.setattr(control, "control_call", lambda *a, **k: {"binary": {"data": b"x" * 16}})
    monkeypatch.setattr(
        control, "save_framebuffer_pngs", lambda *a, **k: {"paths": ["/out/capture_0.png"]}
    )
    assert control.screen_capture() == {"paths": ["/out/capture_0.png"]}


def test_level_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`RE_MCP_LOG_LEVEL` selects the level; default is INFO; OFF is above CRITICAL."""
    monkeypatch.setenv("RE_MCP_LOG_LEVEL", "ERROR")
    assert level_from_env() == logging.ERROR
    monkeypatch.setenv("RE_MCP_LOG_LEVEL", "OFF")
    assert level_from_env() > logging.CRITICAL
    monkeypatch.delenv("RE_MCP_LOG_LEVEL", raising=False)
    assert level_from_env() == logging.INFO
