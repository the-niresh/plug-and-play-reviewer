"""The privacy story must match the live hosted schema, not the original local-only plan."""

from __future__ import annotations

from repo_paths import REPO_ROOT

from pr_reviewer.control_plane.boundary import ALLOWLIST

ROOT = REPO_ROOT

# These phrases were true of the retired `findings` table. They are false now:
# review_findings.title and review_findings.rationale are hosted, allowlisted text.
FALSE_HOSTED_NEVER_SEES_A_FINDING = (
    "Never sees a diff, a finding, or a model key",
    "never holds source, diffs, findings, or model keys",
    "must never get source, diffs, findings, rationale",
    "could hold source or findings are rejected",
)


def test_hosted_stores_finding_title_and_rationale_not_only_opaque_ids() -> None:
    assert ("review_findings", "title") in ALLOWLIST
    assert ("review_findings", "rationale") in ALLOWLIST
    title_reason = ALLOWLIST[("review_findings", "title")].lower()
    rationale_reason = ALLOWLIST[("review_findings", "rationale")].lower()
    assert "findings text" in title_reason
    assert "findings text" in rationale_reason


def test_hosted_finding_text_is_not_a_diff_or_source_hunk() -> None:
    title_reason = ALLOWLIST[("review_findings", "title")].lower()
    rationale_reason = ALLOWLIST[("review_findings", "rationale")].lower()
    assert "never a diff hunk" in title_reason or "never a diff hunk" in rationale_reason
    assert "source" in title_reason
    assert "source" in rationale_reason


def test_operator_docs_do_not_claim_hosted_never_sees_a_finding() -> None:
    files = (
        ROOT / "CLAUDE.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "DATA_BOUNDARIES.md",
        ROOT / "docs" / "SECURITY.md",
        ROOT / "README.md",
    )
    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for phrase in FALSE_HOSTED_NEVER_SEES_A_FINDING:
            if phrase in text:
                offenders.append(f"{path.relative_to(ROOT)}: {phrase}")
    assert offenders == [], f"false privacy claim still present: {offenders}"


def test_operator_docs_say_hosted_stores_finding_title_and_rationale() -> None:
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    boundaries = (ROOT / "docs" / "DATA_BOUNDARIES.md").read_text(encoding="utf-8")
    assert "title" in claude.lower() and "rationale" in claude.lower()
    assert "title" in architecture.lower() and "rationale" in architecture.lower()
    assert "`review_findings`" in boundaries
    assert "`title`" in boundaries
    assert "`rationale`" in boundaries
