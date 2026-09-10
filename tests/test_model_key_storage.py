"""Local setup and review must read model keys from the secret store, not os.environ."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pr_reviewer.agent_surfaces.backend import resolve_model_provider
from pr_reviewer.cli.main import run_setup
from pr_reviewer.models.anthropic_provider import AnthropicProvider
from pr_reviewer.models.openai_provider import OpenAIProvider
from pr_reviewer.runner.secrets import FileSecretStore

STORE_KEY = "sk-ant-from-secret-store"
ENV_KEY = "sk-from-os-environ"


def test_setup_stores_the_model_key_without_writing_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_KEY", raising=False)
    before = dict(os.environ)
    secrets = FileSecretStore(tmp_path / "secrets")
    result = run_setup(
        hosted_origin="https://control.example.test",
        secrets=secrets,
        read_secret=lambda _prompt: STORE_KEY,
        argv=["setup", "--hosted-origin", "https://control.example.test"],
    )
    assert result == 0
    assert secrets.get("model_key") == STORE_KEY
    assert dict(os.environ) == before
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("ANTHROPIC_API_KEY") is None


def test_resolve_model_provider_uses_the_secret_store_not_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    monkeypatch.setenv("OPENAI_API_KEY", ENV_KEY)
    secrets = FileSecretStore(tmp_path / "secrets")
    secrets.set("model_key", STORE_KEY)
    resolved = resolve_model_provider(secrets)
    assert resolved is not None
    provider_name, provider = resolved
    assert provider_name == "anthropic"
    assert isinstance(provider, AnthropicProvider)
    assert provider._api_key == STORE_KEY
    assert provider._api_key != ENV_KEY


def test_resolve_model_provider_ignores_os_environ_when_the_store_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_KEY)
    monkeypatch.setenv("OPENAI_API_KEY", ENV_KEY)
    secrets = FileSecretStore(tmp_path / "secrets")
    assert resolve_model_provider(secrets) is None


def test_resolve_model_provider_uses_openai_for_a_non_anthropic_stored_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    secrets = FileSecretStore(tmp_path / "secrets")
    secrets.set("model_key", "sk-proj-stored-openai-key")
    resolved = resolve_model_provider(secrets)
    assert resolved is not None
    provider_name, provider = resolved
    assert provider_name == "openai"
    assert isinstance(provider, OpenAIProvider)


def test_control_plane_and_config_never_name_model_key_env_vars() -> None:
    roots = (
        Path(__file__).resolve().parent.parent / "src" / "pr_reviewer" / "control_plane",
        Path(__file__).resolve().parent.parent / "src" / "pr_reviewer" / "config.py",
    )
    names = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MODEL_KEY")
    offenders: list[str] = []
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(sorted(root.rglob("*.py")))
    for path in files:
        text = path.read_text(encoding="utf-8")
        for name in names:
            if name in text:
                offenders.append(f"{path.name}:{name}")
    assert offenders == [], f"hosted/config still names a model-key env var: {offenders}"
