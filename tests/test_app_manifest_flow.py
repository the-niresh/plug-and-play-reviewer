from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from pr_reviewer.config import get_settings
from pr_reviewer.github.app_client import GitHubAppClient
from pr_reviewer.github.tokens import GitHubAppSettings
from pr_reviewer.web.app import app


def _rsa_private_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class CapturingManifestHttpClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        self.calls.append({"url": url, "headers": headers, "timeout": timeout, "json": json})
        return httpx.Response(
            201,
            request=httpx.Request("POST", url),
            json=self.payload,
        )


def test_manifest_exchange_stores_credentials_and_they_are_usable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import pr_reviewer.control_plane.app_manifest as app_manifest

    store_path = tmp_path / "github_app_credentials.json"
    private_key = _rsa_private_key_pem()
    converted = {
        "id": 4321,
        "slug": "user-owned-reviewer",
        "pem": private_key,
        "webhook_secret": "whsec_from_manifest",
        "client_id": "Iv1.manifest-client",
        "client_secret": "manifest-client-secret",
    }
    github = CapturingManifestHttpClient(converted)

    monkeypatch.setenv("PR_REVIEWER_HOSTED_ORIGIN", "https://reviewer.example.test")
    monkeypatch.setenv("PR_REVIEWER_APP_MANIFEST_STORE", str(store_path))
    monkeypatch.setenv("GITHUB_APP_ID", "")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "")
    monkeypatch.setattr(app_manifest, "_manifest_http_client", lambda: github)

    client = TestClient(app, base_url="https://testserver")
    begin = client.get("/api/github/app-manifest/start", follow_redirects=False)
    assert begin.status_code == 302

    location = begin.headers["location"]
    params = parse_qs(urlparse(location).query)
    assert "state" in params and params["state"]
    state = params["state"][0]

    complete = client.get(
        "/api/github/app-manifest/callback",
        params={"code": "manifest-code-1", "state": state},
    )
    assert complete.status_code == 200
    assert complete.json()["connected"] is True

    assert store_path.is_file()
    assert store_path.stat().st_mode & 0o777 == 0o600
    stored = json.loads(store_path.read_text(encoding="utf-8"))
    assert stored == {
        "app_id": "4321",
        "private_key": private_key,
        "webhook_secret": "whsec_from_manifest",
        "oauth_client_id": "Iv1.manifest-client",
        "oauth_client_secret": "manifest-client-secret",
    }

    settings = get_settings()
    assert settings.github_app_id == "4321"
    assert settings.github_webhook_secret == "whsec_from_manifest"
    assert settings.github_oauth_client_id == "Iv1.manifest-client"

    sign_in = client.get(
        "/api/auth/github/sign-in",
        params={"return_to": "/dashboard"},
        follow_redirects=False,
    )
    assert sign_in.status_code == 302
    sign_in_qs = parse_qs(urlparse(sign_in.headers["location"]).query)
    assert sign_in_qs["client_id"] == ["Iv1.manifest-client"]

    token_client = CapturingManifestHttpClient(
        {"token": "ghs_after_manifest", "expires_at": "2026-01-01T01:00:00Z"}
    )
    app_client = GitHubAppClient(
        settings=GitHubAppSettings(
            app_id=settings.github_app_id,
            private_key=settings.github_app_private_key,
        ),
        client=token_client,
    )
    minted = app_client.create_installation_token(
        1001,
        repository_ids=[2002],
        permissions={"contents": "read", "pull_requests": "read"},
    )
    assert minted.token == "ghs_after_manifest"
    assert token_client.calls
    assert token_client.calls[0]["headers"]["authorization"].startswith("Bearer ")

    blocked = client.get("/api/github/app-manifest/start", follow_redirects=False)
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "already_configured"


def test_bootstrap_ignores_malformed_manifest_credentials_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import pr_reviewer.control_plane.app_manifest as app_manifest

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")

    monkeypatch.setenv("PR_REVIEWER_APP_MANIFEST_STORE", str(broken))
    monkeypatch.setenv("GITHUB_APP_ID", "")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "")

    app_manifest.bootstrap_manifest_credentials_into_environment()
    assert os.environ.get("GITHUB_APP_ID") == ""
