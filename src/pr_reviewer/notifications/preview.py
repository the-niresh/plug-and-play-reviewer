"""Notification title and body. Restricted titles must not name the finding."""

from __future__ import annotations

from collections.abc import Sequence

from pr_reviewer.contracts.finding import Finding
from pr_reviewer.contracts.notification import Confidentiality, NotificationPreview

RESTRICTED_TITLE = "Review finding needs attention"


def build_preview(finding: Finding, *, confidentiality: Confidentiality) -> NotificationPreview:
    if confidentiality == "restricted":
        return NotificationPreview(
            title=RESTRICTED_TITLE,
            body=(
                f"{finding.title}\n{finding.file_path}:{finding.line_start}\n{finding.rationale}"
            ),
            confidentiality=confidentiality,
        )
    return NotificationPreview(
        title="Your pull request was reviewed",
        body="A review finished.",
        confidentiality=confidentiality,
    )


def build_review_summary_preview(
    findings: Sequence[Finding],
    *,
    pull_request: str,
    confidentiality: Confidentiality,
) -> NotificationPreview:
    """One ping for a whole review, rather than one per finding.

    Same rule as build_preview: a restricted title must not name a finding, because the
    title is what a notification popup shows on a screen someone else can see. A count
    and a pull request reference name no finding, so both stay in the title where they
    are useful.
    """
    if confidentiality != "restricted":
        return NotificationPreview(
            title="Your pull request was reviewed",
            body="A review finished.",
            confidentiality=confidentiality,
        )
    noun = "finding" if len(findings) == 1 else "findings"
    lines = [
        f"{finding.title}\n  {finding.file_path}:{finding.line_start}  "
        f"({finding.severity}, {finding.concern})"
        for finding in findings
    ]
    return NotificationPreview(
        title=f"{pull_request}: {len(findings)} {noun} need attention",
        body="\n".join(lines),
        confidentiality=confidentiality,
    )
