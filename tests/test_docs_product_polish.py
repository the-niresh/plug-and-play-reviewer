"""Public docs must match the product on the landing page.

These checks fail if a new reader still gets a builder log, a dead-hostname
claim, or a false privacy story. They read the markdown, not a function call.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
INSTALL = ROOT / "docs" / "INSTALL.md"
DEPLOY = ROOT / "docs" / "DEPLOY.md"
RUNBOOK = ROOT / "docs" / "RUNBOOK.md"
SECURITY = ROOT / "docs" / "SECURITY.md"
ARCHITECTURE = ROOT / "docs" / "ARCHITECTURE.md"
DEMO = ROOT / "docs" / "DEMO.md"
BOUNDARIES = ROOT / "docs" / "DATA_BOUNDARIES.md"

PUBLIC_DOCS = (
    README,
    INSTALL,
    DEPLOY,
    RUNBOOK,
    SECURITY,
    ARCHITECTURE,
    DEMO,
    BOUNDARIES,
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_first_screen_explains_the_product() -> None:
    head = "\n".join(_text(README).splitlines()[:25])
    lowered = head.lower()
    assert "pr reviewer" in lowered
    assert "hosted" in lowered
    assert "runner" in lowered
    assert "source" in lowered
    assert "diff" in lowered
    assert "model key" in lowered


def test_readme_is_not_the_old_builder_log() -> None:
    text = _text(README)
    assert "Private. Not a public package." not in text
    assert "reviewer.niresh.tech` is not live" not in text
    assert "Last recorded backend suite on this branch: 747" not in text


def test_docs_name_retrieval_suggestions_specialists_and_eval_limits() -> None:
    blob = "\n".join(_text(path) for path in (README, ARCHITECTURE, DEMO))
    lowered = blob.lower()
    assert "retrieval" in lowered
    assert "suggested fix" in lowered or "suggestion" in lowered
    assert "opt-in" in lowered
    assert "off by default" in lowered
    assert "not a baseline" in lowered or "not a published baseline" in lowered
    assert "self-improving" not in lowered


def test_docs_state_the_paid_team_path_without_prices() -> None:
    blob = "\n".join(_text(path) for path in (README, ARCHITECTURE))
    lowered = blob.lower()
    assert "paid path" in lowered
    assert "team" in lowered
    assert "$" not in blob or "cost" in lowered


def test_install_says_what_you_need_before_starting() -> None:
    text = _text(INSTALL)
    lowered = text.lower()
    assert "before you start" in lowered or "what you need" in lowered
    assert "model key" in lowered
    assert "hosted" in lowered
    assert "github" in lowered


def test_deploy_and_runbook_separate_proved_from_owner_setup() -> None:
    deploy = _text(DEPLOY)
    runbook = _text(RUNBOOK)
    assert "reviewer.niresh.tech" in deploy
    assert "/health" in deploy
    assert "DATABASE_URL" in deploy
    assert "GITHUB_APP_ID" in deploy
    assert "proved" in runbook.lower() or "live" in runbook.lower()
    assert "owner" in runbook.lower() or "still" in runbook.lower()
    assert "Nothing in this file is applied" not in runbook


def test_security_and_boundaries_match_the_hosted_local_split() -> None:
    security = _text(SECURITY).lower()
    boundaries = _text(BOUNDARIES).lower()
    for text in (security, boundaries):
        assert "source" in text
        assert "diff" in text
        assert "model key" in text
        assert "title" in text
        assert "rationale" in text
    assert "never" in security


def test_demo_does_not_say_the_live_host_is_missing() -> None:
    text = _text(DEMO)
    assert "does not exist yet" not in text
    assert "reviewer.niresh.tech" in text


def test_public_docs_do_not_claim_self_improving() -> None:
    for path in PUBLIC_DOCS:
        lowered = _text(path).lower()
        assert "self-improving" not in lowered, path.name


def test_demo_records_live_github_proof_without_eval_baseline() -> None:
    text = _text(DEMO)
    lowered = text.lower()
    assert "live-github-loop-proof.md" in text
    assert "public-install-live-review-proof.md" in text
    assert "clean-machine-install-proof.md" in text
    assert "review_comment_feedback" in lowered
    assert "not a baseline" in lowered or "not a published baseline" in lowered
    assert "self-improving" not in lowered


def test_readme_names_the_narrow_published_baseline() -> None:
    text = _text(README).lower()
    assert "zod" in text
    assert "holdout" in text
    assert "7" in text or "seven" in text
    assert "not proof on every" in text or "not proof on every language" in text


def test_install_does_not_document_stale_curl_404_fallback() -> None:
    text = _text(INSTALL)
    assert "returns **404**" not in text
    assert "http 200" in text.lower() or "200" in text


def test_runbook_links_live_proof_reports() -> None:
    text = _text(RUNBOOK)
    for report in (
        "clean-machine-install-proof.md",
        "public-install-live-review-proof.md",
        "live-github-loop-proof.md",
        "holdout-quality-baseline.md",
    ):
        assert report in text


def test_readme_states_free_tier_without_prices() -> None:
    text = _text(README).lower()
    assert "free tier" in text
    assert "one github user" in text or "one repository" in text


def test_release_doc_describes_checksum_install_path() -> None:
    release = (ROOT / "docs" / "RELEASE.md").read_text(encoding="utf-8").lower()
    install = _text(INSTALL).lower()
    assert "sha256sums" in release
    assert "install-from-release.sh" in release
    assert "install-from-release.sh" in install
    assert "release.md" in install
