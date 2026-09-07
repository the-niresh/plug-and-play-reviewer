"""Deployment secret source rules for Phase 35 C5."""

from __future__ import annotations

import os
from pathlib import Path


class _AvailableKeyringBackend:
    def get_password(self, service: str, name: str) -> str | None:
        del service, name
        return "keyring-value"

    def set_password(self, service: str, name: str, value: str) -> None:
        del service, name, value

    def delete_password(self, service: str, name: str) -> None:
        del service, name


def test_provider_key_is_read_from_mounted_file_never_from_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from pr_reviewer.runner.secrets import FileSecretStore, get_secret_store

    mounted_dir = tmp_path / "mounted-secrets"
    mounted = FileSecretStore(mounted_dir)
    mounted.set("model_key", "file-provider-key")

    monkeypatch.setenv("PR_REVIEWER_SECRET_FILES_DIR", str(mounted_dir))
    monkeypatch.setenv("MODEL_KEY", "env-provider-key")
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic-key")

    before = dict(os.environ)
    store = get_secret_store(
        file_fallback_directory=tmp_path / "fallback-secrets",
        keyring_backend=_AvailableKeyringBackend(),
    )
    assert store.get("model_key") == "file-provider-key"
    assert store.get("model_key") != os.environ["MODEL_KEY"]
    assert dict(os.environ) == before

    mounted.delete("model_key")
    assert store.get("model_key") is None


def test_configured_mounted_secret_directory_must_exist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from pr_reviewer.runner.secrets import get_secret_store

    missing = tmp_path / "missing-mount"
    monkeypatch.setenv("PR_REVIEWER_SECRET_FILES_DIR", str(missing))

    try:
        get_secret_store(file_fallback_directory=tmp_path / "fallback-secrets")
    except RuntimeError as exc:
        assert "PR_REVIEWER_SECRET_FILES_DIR" in str(exc)
    else:
        raise AssertionError("expected configured mounted secret directory to fail closed")
