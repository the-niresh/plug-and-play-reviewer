"""Deploy blueprints for one-click Render and Railway setup (Phase 35 C5)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RENDER_BLUEPRINT = REPO / "deploy" / "render.yaml"
RAILWAY_TEMPLATE = REPO / "deploy" / "railway.json"

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


def test_render_blueprint_uses_one_web_process_with_boot_config_only() -> None:
    text = RENDER_BLUEPRINT.read_text(encoding="utf-8")
    assert text.count("- type: web") == 1
    assert "name: reviewer" in text
    assert "/app/.venv/bin/pr-reviewer-api" in text
    assert "NEXT_PUBLIC_CONTROL_PLANE_ORIGIN" not in text
    assert "Access-Control-Allow-Origin" not in text
    assert "cors" not in text.lower()
    for key in REQUIRED_BOOT_ENV:
        assert f"key: {key}" in text
    assert "key: PR_REVIEWER_SECRET_FILES_DIR" in text
    assert "value: /run/secrets/pr-reviewer" in text
    for key in FORBIDDEN_RUNTIME_SECRET_ENV:
        assert f"key: {key}" not in text
    assert "mountPath: /run/secrets/pr-reviewer" in text


def test_railway_template_uses_one_service_and_no_browser_to_api_split() -> None:
    payload = json.loads(RAILWAY_TEMPLATE.read_text(encoding="utf-8"))
    service = payload["service"]
    assert service["name"] == "reviewer"
    assert service["startCommand"] == "/app/.venv/bin/pr-reviewer-api"
    assert service["healthcheckPath"] == "/health"
    environment = service["environment"]
    for key in REQUIRED_BOOT_ENV:
        assert key in environment
    assert environment["PR_REVIEWER_SECRET_FILES_DIR"] == "/run/secrets/pr-reviewer"
    for key in FORBIDDEN_RUNTIME_SECRET_ENV:
        assert key not in environment
    assert "NEXT_PUBLIC_CONTROL_PLANE_ORIGIN" not in environment
    assert payload["volumes"][0]["mountPath"] == "/run/secrets/pr-reviewer"
