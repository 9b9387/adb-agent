"""Tests for the ADK Web launcher helpers."""

from adk_web_agents.cli import _pick_port


def test_pick_port_respects_explicit_port():
    port, auto_switched = _pick_port("127.0.0.1", 8099)

    assert port == 8099
    assert auto_switched is False


def test_pick_port_chooses_next_free_port(monkeypatch):
    ports = {
        8000: False,
        8001: False,
        8002: True,
    }

    monkeypatch.setattr(
        "adk_web_agents.cli._is_port_available",
        lambda host, port: ports.get(port, True),
    )
    monkeypatch.setenv("ADK_WEB_PORT", "8000")

    port, auto_switched = _pick_port("127.0.0.1", None)

    assert port == 8002
    assert auto_switched is True
