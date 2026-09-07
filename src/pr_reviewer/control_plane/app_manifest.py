"""GitHub App Manifest handshake for user-owned app setup."""

from __future__ import annotations

import json
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from pr_reviewer.config import get_settings
from pr_reviewer.control_plane.github_oauth import STATE_TTL_SECONDS
from pr_reviewer.control_plane.repository_policy import hash_runner_credential
from pr_reviewer.db.client import connection

router = APIRouter(prefix="/api/github/app-manifest", tags=["github-app-manifest"])

CALLBACK_PATH = "/api/github/app-manifest/callback"
WEBHOOK_PATH = "/api/github/webhook"
GITHUB_MANIFEST_CREATE_URL = "https://github.com/settings/apps/new"
BINDING_COOKIE_NAME = "gh_manifest_binding"
DEFAULT_MANIFEST_NAME = "PR Reviewer"
STORE_PATH_ENV = "PR_REVIEWER_APP_MANIFEST_STORE"
DEFAULT_STORE_PATH = Path.home() / ".config" / "pr-reviewer" / "github_app_credentials.json"
MANIFEST_CONVERSION_URL = "https://api.github.com/app-manifests/{code}/conversions"


class ManifestHttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
        json: dict[str, object] | None = None,
    ) -> httpx.Response: ...


@dataclass(frozen=True)
class StoredAppCredentials:
    app_id: str
    private_key: str
    webhook_secret: str
    oauth_client_id: str
    oauth_client_secret: str


@dataclass(frozen=True)
class ManifestStart:
    state: str
    binding_secret: str
    expires_at_iso: str


@dataclass(frozen=True)
class ConvertedGitHubApp:
    app_id: str
    private_key: str
    webhook_secret: str
    oauth_client_id: str
    oauth_client_secret: str
    slug: str


@router.get("/start")
def start_manifest_flow_route() -> RedirectResponse:
    if credentials_already_configured():
        raise HTTPException(status_code=409, detail="already_configured")
    origin = get_settings().hosted_origin
    if not origin.startswith("https://"):
        raise HTTPException(status_code=500, detail="hosted_origin_not_configured")
    start = begin_manifest_flow()
    manifest = build_app_manifest(origin)
    query = urlencode(
        {
            "state": start.state,
            "manifest": json.dumps(manifest, separators=(",", ":")),
        }
    )
    response = RedirectResponse(url=f"{GITHUB_MANIFEST_CREATE_URL}?{query}", status_code=302)
    response.set_cookie(
        key=BINDING_COOKIE_NAME,
        value=start.binding_secret,
        max_age=STATE_TTL_SECONDS,
        path=CALLBACK_PATH,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/callback")
def complete_manifest_flow_route(code: str, state: str, request: Request) -> JSONResponse:
    if credentials_already_configured():
        raise HTTPException(status_code=409, detail="already_configured")
    binding_secret = request.cookies.get(BINDING_COOKIE_NAME, "")
    if not consume_manifest_state(state, binding_secret):
        raise HTTPException(status_code=401, detail="invalid_or_expired_state")
    converted = exchange_manifest_code(code, http_client=_manifest_http_client())
    store_path = manifest_store_path()
    persist_manifest_credentials(store_path, converted)
    apply_manifest_credentials_to_environment(converted)
    return JSONResponse(
        {
            "connected": True,
            "app_id": converted.app_id,
            "app_slug": converted.slug,
        }
    )


def begin_manifest_flow() -> ManifestStart:
    state = secrets.token_urlsafe(32)
    binding_secret = secrets.token_urlsafe(32)
    with connection() as conn:
        row = conn.execute(
            """
            insert into oauth_states (state_hash, binding_hash, return_to, pairing_code_hash)
            values (%s, %s, %s, null)
            returning created_at
            """,
            (
                hash_runner_credential(state),
                hash_runner_credential(binding_secret),
                "/dashboard",
            ),
        ).fetchone()
    assert row is not None
    expires_at = row["created_at"] + timedelta(seconds=STATE_TTL_SECONDS)
    return ManifestStart(
        state=state,
        binding_secret=binding_secret,
        expires_at_iso=expires_at.isoformat(),
    )


def consume_manifest_state(state: str, binding_secret: str) -> bool:
    with connection() as conn, conn.transaction():
        row = conn.execute(
            """
            update oauth_states
            set consumed_at = now()
            where state_hash = %s
              and binding_hash = %s
              and consumed_at is null
              and created_at > now() - interval '10 minutes'
            returning id
            """,
            (hash_runner_credential(state), hash_runner_credential(binding_secret)),
        ).fetchone()
    return row is not None


def build_app_manifest(hosted_origin: str) -> dict[str, object]:
    return {
        "name": DEFAULT_MANIFEST_NAME,
        "url": hosted_origin,
        "redirect_url": hosted_origin + CALLBACK_PATH,
        "callback_urls": [hosted_origin + "/api/auth/github/callback"],
        "setup_url": hosted_origin + "/api/auth/github/sign-in?return_to=/dashboard",
        "hook_attributes": {"url": hosted_origin + WEBHOOK_PATH},
        "default_permissions": {
            "contents": "read",
            "pull_requests": "read",
            "metadata": "read",
        },
        "default_events": [
            "pull_request",
            "installation",
            "installation_repositories",
        ],
        "request_oauth_on_install": True,
        "public": False,
    }


def exchange_manifest_code(
    code: str,
    *,
    http_client: ManifestHttpClient | None = None,
) -> ConvertedGitHubApp:
    client = http_client or _manifest_http_client()
    response = client.post(
        MANIFEST_CONVERSION_URL.format(code=code),
        headers={
            "accept": "application/vnd.github+json",
            "x-github-api-version": "2022-11-28",
        },
        timeout=10.0,
        json=None,
    )
    response.raise_for_status()
    body = _as_mapping(response.json())
    converted = ConvertedGitHubApp(
        app_id=_required_text(body, "id"),
        private_key=_required_text(body, "pem"),
        webhook_secret=_required_text(body, "webhook_secret"),
        oauth_client_id=_required_text(body, "client_id"),
        oauth_client_secret=_required_text(body, "client_secret"),
        slug=_required_text(body, "slug"),
    )
    return converted


def persist_manifest_credentials(path: Path, converted: ConvertedGitHubApp) -> None:
    payload = {
        "app_id": converted.app_id,
        "private_key": converted.private_key,
        "webhook_secret": converted.webhook_secret,
        "oauth_client_id": converted.oauth_client_id,
        "oauth_client_secret": converted.oauth_client_secret,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(path)


def apply_manifest_credentials_to_environment(converted: ConvertedGitHubApp) -> None:
    os.environ["GITHUB_APP_ID"] = converted.app_id
    os.environ["GITHUB_APP_PRIVATE_KEY"] = converted.private_key
    os.environ["GITHUB_WEBHOOK_SECRET"] = converted.webhook_secret
    os.environ["GITHUB_OAUTH_CLIENT_ID"] = converted.oauth_client_id
    os.environ["GITHUB_OAUTH_CLIENT_SECRET"] = converted.oauth_client_secret


def load_manifest_credentials(path: Path) -> StoredAppCredentials | None:
    if not path.is_file():
        return None
    try:
        data = _as_mapping(json.loads(path.read_text(encoding="utf-8")))
        return StoredAppCredentials(
            app_id=_required_text(data, "app_id"),
            private_key=_required_text(data, "private_key"),
            webhook_secret=_required_text(data, "webhook_secret"),
            oauth_client_id=_required_text(data, "oauth_client_id"),
            oauth_client_secret=_required_text(data, "oauth_client_secret"),
        )
    except (json.JSONDecodeError, OSError, RuntimeError, TypeError, ValueError):
        return None


def bootstrap_manifest_credentials_into_environment() -> None:
    if _all_required_environment_credentials_are_set():
        return
    stored = load_manifest_credentials(manifest_store_path())
    if stored is None:
        return
    os.environ["GITHUB_APP_ID"] = stored.app_id
    os.environ["GITHUB_APP_PRIVATE_KEY"] = stored.private_key
    os.environ["GITHUB_WEBHOOK_SECRET"] = stored.webhook_secret
    os.environ["GITHUB_OAUTH_CLIENT_ID"] = stored.oauth_client_id
    os.environ["GITHUB_OAUTH_CLIENT_SECRET"] = stored.oauth_client_secret


def manifest_store_path() -> Path:
    configured = os.environ.get(STORE_PATH_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_STORE_PATH


def _manifest_http_client() -> ManifestHttpClient:
    return httpx.Client()


def credentials_already_configured() -> bool:
    return _all_required_environment_credentials_are_set() or manifest_store_path().is_file()


def _all_required_environment_credentials_are_set() -> bool:
    required = (
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_OAUTH_CLIENT_ID",
        "GITHUB_OAUTH_CLIENT_SECRET",
    )
    return all(bool(os.environ.get(name, "").strip()) for name in required)


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    text = str(value) if value is not None else ""
    if not text:
        raise RuntimeError(f"manifest conversion response missing {key}")
    return text


def _as_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, dict):
        return value
    raise RuntimeError("manifest conversion response must be a JSON object")
