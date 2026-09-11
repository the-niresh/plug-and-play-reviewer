"""Interactive reviewer setup wizard."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from pr_reviewer.runner.secrets import FileSecretStore

EXPECTED_PROVIDER_IDS = frozenset(
    {
        "openai",
        "anthropic",
        "moonshot",
        "qwen",
        "openrouter",
        "groq",
        "xai",
        "deepseek",
        "github-copilot",
        "ollama",
        "opencode",
    }
)


def test_catalogue_lists_all_eleven_providers() -> None:
    from pr_reviewer.models.catalogue import CATALOGUE

    provider_ids = {provider.provider_id for provider in CATALOGUE}
    assert provider_ids == EXPECTED_PROVIDER_IDS


def test_catalogue_entries_include_base_url() -> None:
    from pr_reviewer.models.catalogue import CATALOGUE, base_url_for

    for provider in CATALOGUE:
        assert provider.base_url
        assert base_url_for(provider.provider_id) == provider.base_url


def test_models_for_ollama_returns_models() -> None:
    from pr_reviewer.models.catalogue import models_for

    models = models_for("ollama")
    assert models
    assert all(entry.model_id for entry in models)


def test_setup_wizard_stores_model_key_with_plain_wording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pr_reviewer.cli.main import run_setup

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    secrets = FileSecretStore(config_dir)
    key = "sk-proj-wizard-test-key"
    prompts: list[str] = []

    def read_secret(prompt: str) -> str:
        prompts.append(prompt)
        return key

    result = run_setup(
        secrets=secrets,
        read_secret=read_secret,
        argv=["setup", "--quick"],
        stdin=io.StringIO(""),
        stdout=io.StringIO(),
    )

    assert result == 0
    assert secrets.get("model_key") == key
    assert prompts
    assert "Model API key" not in prompts[0]
    assert "LLM provider API key" in prompts[0]


def test_setup_wizard_quick_skips_sections_when_config_complete(
    tmp_path: Path,
) -> None:
    from pr_reviewer.cli.main import run_setup
    from pr_reviewer.runner.cli.setup_wizard import SetupConfig, save_setup_config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    secrets = FileSecretStore(config_dir)
    secrets.set("model_key", "sk-ant-already-set")
    save_setup_config(
        SetupConfig(
            provider_id="anthropic",
            model_id="claude-haiku-4-5-20251001",
            hosted_origin="https://control.example.test",
            prompt_name="diff_only_reviewer",
            prompt_version="1",
            custom_base_url=None,
            custom_model_id=None,
        ),
        config_dir=config_dir,
    )
    out = io.StringIO()

    result = run_setup(
        secrets=secrets,
        read_secret=lambda _prompt: "",
        argv=["setup", "--quick"],
        stdin=io.StringIO(""),
        stdout=out,
        config_dir=config_dir,
    )

    assert result == 0
    assert "your LLM provider API key" not in out.getvalue().lower()


def test_setup_wizard_prints_paths_up_front(tmp_path: Path) -> None:
    from pr_reviewer.cli.main import run_setup

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    secrets = FileSecretStore(config_dir)
    out = io.StringIO()

    run_setup(
        secrets=secrets,
        read_secret=lambda _prompt: "sk-test-key",
        argv=["setup", "--quick"],
        stdin=io.StringIO(""),
        stdout=out,
        config_dir=config_dir,
    )

    text = out.getvalue()
    assert str(config_dir) in text
    assert "Configuration Location" in text


def test_radio_select_marks_current_choice() -> None:
    from pr_reviewer.runner.cli.setup_wizard import radio_select

    stdin = io.StringIO("\n")
    stdout = io.StringIO()
    choice = radio_select(
        "Pick one",
        options=("alpha", "beta", "gamma"),
        current="beta",
        stdin=stdin,
        stdout=stdout,
    )

    assert choice == "beta"
    rendered = stdout.getvalue()
    assert "currently active" in rendered
    assert "beta" in rendered
    assert "navigate" in rendered.lower() or "↑↓" in rendered
