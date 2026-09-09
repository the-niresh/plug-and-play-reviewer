"""Deploy blueprints for one-click Render and Railway setup (Phase 35 C5)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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
