"""Deploy blueprints for one-click Render and Railway setup (Phase 35 C5)."""

from __future__ import annotations

import json

import yaml
from repo_paths import REPO_ROOT

REPO = REPO_ROOT
RENDER_BLUEPRINT = REPO / "deploy" / "render.yaml"
RAILWAY_TEMPLATE = REPO / "deploy" / "railway.json"
DEPLOY_GUIDE = REPO / "docs" / "DEPLOY.md"

REQUIRED_BOOT_ENV = (
    "DATABASE_URL",
    "GITHUB_APP_ID",
    "GITHUB_APP_PRIVATE_KEY",
    "GITHUB_OAUTH_CLIENT_ID",
    "GITHUB_OAUTH_CLIENT_SECRET",
    "GITHUB_WEBHOOK_SECRET",
    "PR_REVIEWER_HOSTED_ORIGIN",
)

FORBIDDEN_RUNTIME_SECRET_ENV = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "MODEL_KEY")
MIGRATE = "/app/.venv/bin/pr-reviewer-db-migrate"
API = "/app/.venv/bin/pr-reviewer-api"


def test_render_blueprint_uses_one_web_process_with_boot_config_only() -> None:
    text = RENDER_BLUEPRINT.read_text(encoding="utf-8")
    assert text.count("- type: web") == 1
    assert "name: reviewer" in text
    assert API in text
    assert f"preDeployCommand: {MIGRATE}" in text
    assert "NEXT_PUBLIC_CONTROL_PLANE_ORIGIN" not in text
    assert "Access-Control-Allow-Origin" not in text
    assert "cors" not in text.lower()
    for key in REQUIRED_BOOT_ENV:
        assert f"key: {key}" in text
    assert "key: PR_REVIEWER_SECRET_FILES_DIR" not in text
    assert "disk:" not in text
    for key in FORBIDDEN_RUNTIME_SECRET_ENV:
        assert f"key: {key}" not in text


def test_render_blueprint_provisions_and_wires_its_own_database() -> None:
    """One-click means one-click: the user should not have to find and paste a
    Postgres URL by hand. Render can provision Postgres with pgvector, and
    db/migrations/0001_initial.sql already runs `create extension if not
    exists vector`, so a Render-managed database works here.
    """
    payload = yaml.safe_load(RENDER_BLUEPRINT.read_text(encoding="utf-8"))
    databases = payload["databases"]
    assert any(db["name"] == "reviewer-db" for db in databases)

    env_vars = payload["services"][0]["envVars"]
    database_url_entry = next(entry for entry in env_vars if entry["key"] == "DATABASE_URL")
    assert database_url_entry["fromDatabase"]["name"] == "reviewer-db"
    assert database_url_entry["fromDatabase"]["property"] == "connectionString"
    assert "sync" not in database_url_entry

    # The other six control-plane variables are still user-supplied.
    manual_keys = {key for key in REQUIRED_BOOT_ENV if key != "DATABASE_URL"}
    for entry in env_vars:
        if entry["key"] in manual_keys:
            assert entry.get("sync") is False


def test_no_deploy_file_ever_gets_a_model_key_variable() -> None:
    """Model keys belong on the runner, never the control plane. This test
    fails on sight if someone later adds OPENAI_API_KEY, ANTHROPIC_API_KEY, or
    model_key to either deploy file, in any casing or nesting.
    """
    render_text = RENDER_BLUEPRINT.read_text(encoding="utf-8").lower()
    railway_text = RAILWAY_TEMPLATE.read_text(encoding="utf-8").lower()
    for forbidden in FORBIDDEN_RUNTIME_SECRET_ENV:
        assert forbidden.lower() not in render_text
        assert forbidden.lower() not in railway_text


def test_railway_template_matches_the_railway_schema_and_migrates_on_deploy() -> None:
    payload = json.loads(RAILWAY_TEMPLATE.read_text(encoding="utf-8"))
    assert "service" not in payload
    assert "volumes" not in payload
    deploy = payload["deploy"]
    assert deploy["startCommand"] == API
    assert deploy["healthcheckPath"] == "/health"
    assert deploy["preDeployCommand"] == MIGRATE
    environment = payload.get("deploy", {}).get("environment", {})
    for key in FORBIDDEN_RUNTIME_SECRET_ENV:
        assert key not in environment
    assert "NEXT_PUBLIC_CONTROL_PLANE_ORIGIN" not in json.dumps(payload)


def test_deploy_guide_names_every_boot_env_and_the_health_paths() -> None:
    guide = DEPLOY_GUIDE.read_text(encoding="utf-8")
    for key in REQUIRED_BOOT_ENV:
        assert key in guide
    assert "/health" in guide
    assert "/ready" in guide
    assert "pr-reviewer-db-migrate" in guide
