"""Hosted API boot must work on Render and Railway, not only on port 8000."""

from __future__ import annotations

import importlib

hosted_app = importlib.import_module("pr_reviewer.control_plane.app")


def test_hosted_api_listens_on_port_from_the_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*_args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setenv("PORT", "24680")
    monkeypatch.setattr(hosted_app.uvicorn, "run", fake_run)
    hosted_app.main()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 24680
    assert captured.get("reload") is False


def test_hosted_api_defaults_to_port_8000_without_reload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*_args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(hosted_app.uvicorn, "run", fake_run)
    hosted_app.main()
    assert captured["port"] == 8000
    assert captured.get("reload") is False
