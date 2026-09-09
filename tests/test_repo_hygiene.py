"""Public repository files a stranger expects before launch."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_root_security_policy_points_to_private_reporting() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "docs/security.md" in lowered
    assert "security/advisories/new" in lowered
    assert "prompt injection" in lowered
    assert "data-boundary" in lowered
    assert "do not promise a fixed response time" in lowered


def test_code_of_conduct_exists() -> None:
    text = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8").lower()
    assert "code of conduct" in text
    assert "harassment" in text


def test_github_issue_templates_exist() -> None:
    config = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    bug = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
    assert config.is_file()
    assert bug.is_file()
    config_text = config.read_text(encoding="utf-8")
    bug_text = bug.read_text(encoding="utf-8")
    assert "security/advisories/new" in config_text
    assert "prompt injection" in bug_text.lower()


def test_pull_request_template_asks_for_gate_results() -> None:
    text = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8").lower()
    assert "red proof" in text
    assert "ruff" in text
    assert "mypy" in text
    assert "pytest" in text
    assert "data-boundary" in text


def test_repo_topics_checklist_exists() -> None:
    text = (ROOT / "docs" / "REPO_TOPICS.md").read_text(encoding="utf-8")
    assert "gh repo edit" in text
    assert "code-review" in text
    assert "github-app" in text
