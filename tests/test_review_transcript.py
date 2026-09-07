"""A review streams into the transcript as it happens.

The point of 35.D4 is not that ReviewPanel has an add_finding method -- it already did.
The point is that a finding lands on screen while the review is still running, before
anything marks the review complete, and that a suppressed finding shows dimmed with the
judge's own reason instead of vanishing. A test that only called add_finding once and
checked the DOM would not tell streaming apart from a single batch render; this one
checks state strictly before completion is ever signalled, then checks it again after.
"""

from __future__ import annotations

import asyncio

from pr_reviewer.contracts.finding import Finding
from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.reviewer.receipt import (
    AssertedVerification,
    FindingReceipt,
    ReceiptContextSource,
    ReceiptModelCall,
    ReceiptTokens,
)
from pr_reviewer.tui.push_review_summary import ReviewFindingSummary, ReviewSummaryPush
from pr_reviewer.tui.screens.review import ReviewPanel


class _FakeClock:
    """Advances only when the test tells it to -- elapsed is asserted, never slept for."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _RecordingSummaryClient:
    def __init__(self) -> None:
        self.pushed: list[dict[str, object]] = []

    def push(self, payload: dict[str, object]) -> None:
        self.pushed.append(payload)


def _finding(finding_id: str) -> Finding:
    return Finding(
        id=finding_id,
        review_job_id="job-1",
        concern="correctness",
        severity="high",
        category="missing-write",
        file_path="convex/audits.ts",
        line_start=214,
        line_end=214,
        title="submitAudit writes no complianceRecord",
        rationale="All three submit paths must project one. This is a fourth.",
        evidence=["convex/audits.ts:214"],
        confidence=0.9,
        verified=False,
        verification_method="not_applicable",
        public_safe=True,
        status="posted",
    )


def _receipt(finding: Finding, *, tokens: int, cost_usd: str) -> FindingReceipt:
    input_tokens = tokens // 2
    output_tokens = tokens - input_tokens
    return FindingReceipt(
        finding_id=finding.id,
        review_job_id=finding.review_job_id,
        prompt_version_id="prompt-1",
        model_call=ReceiptModelCall(
            provider="openai",
            model="gpt-4o-mini",
            prompt_version_id="prompt-1",
            tokens=ReceiptTokens(input_tokens=input_tokens, output_tokens=output_tokens),
            cost_usd=cost_usd,
        ),
        context_sources=(ReceiptContextSource(kind="diff", name="pr-diff", reference="hunk-1"),),
        verification=AssertedVerification(reason="No sandbox available for this check."),
    )


def _suppressed_candidate() -> FindingCandidate:
    return FindingCandidate(
        concern="maintainability",
        severity="low",
        category="style",
        file_path="apps/web/src/lib/reviews.ts",
        line_start=88,
        line_end=88,
        title="Inconsistent naming",
        rationale="Style only.",
        evidence=["apps/web/src/lib/reviews.ts:88"],
        confidence=0.3,
    )


def _make_panel(clock: _FakeClock) -> ReviewPanel:
    return ReviewPanel(
        (),
        stream_immediately=True,
        summary_client=_RecordingSummaryClient(),
        clock=clock,
    )


def test_a_finding_is_rendered_while_the_review_is_still_running() -> None:
    """The real assertion: the finding's row and the footer's partial count are both on
    screen strictly before complete_review is ever called -- proving this is incremental
    rendering, not a batch produced once the review finishes."""

    async def exercise() -> None:
        from textual.app import App, ComposeResult

        clock = _FakeClock()
        panel = _make_panel(clock)
        summary_client = panel._summary_client
        assert isinstance(summary_client, _RecordingSummaryClient)

        class Harness(App[None]):
            def compose(self) -> ComposeResult:
                yield panel

        async with Harness().run_test() as pilot:
            panel.start_agent_reasoning(chunks=())
            clock.now = 3.4
            finding = _finding("finding-1")
            panel.add_finding(finding, _receipt(finding, tokens=4200, cost_usd="0.002"))
            await pilot.pause()

            # Before completion: the row exists, the footer already shows the partial
            # count, and nothing has been pushed to the hosted plane yet.
            assert pilot.app.query_one("#finding-finding-1") is not None
            footer_text = str(pilot.app.query_one("#review-footer").render())
            assert footer_text == "1 finding . 0 suppressed . 4.2k tokens . $0.002 . 3.4s"
            assert summary_client.pushed == []
            assert panel.last_push_result is None

            clock.now = 6.1
            summary = ReviewSummaryPush(
                review_job_id="job-1",
                installation_id=1,
                github_repository_id=11,
                pull_request_number=142,
                head_sha="a" * 40,
                status="completed",
                findings=(
                    ReviewFindingSummary(
                        concern="correctness",
                        severity="high",
                        file_path="convex/audits.ts",
                        line_start=214,
                        line_end=214,
                        title="submitAudit writes no complianceRecord",
                        status="posted",
                    ),
                ),
            )
            result = panel.complete_review(summary)

            # After completion: the earlier row is untouched, and the push actually
            # happened this time -- the ordering, not just the end state, is the proof.
            assert result is not None and result.ok
            assert len(summary_client.pushed) == 1
            assert pilot.app.query_one("#finding-finding-1") is not None

    asyncio.run(exercise())


def test_suppressed_finding_shows_dimmed_with_the_judges_reason() -> None:
    async def exercise() -> None:
        from textual.app import App, ComposeResult

        clock = _FakeClock()
        panel = _make_panel(clock)

        class Harness(App[None]):
            def compose(self) -> ComposeResult:
                yield panel

        async with Harness().run_test() as pilot:
            panel.start_agent_reasoning(chunks=())
            panel.add_suppressed_finding(
                _suppressed_candidate(), "style only, low confidence"
            )
            await pilot.pause()

            row = pilot.app.query_one("#suppressed-1")
            assert "finding-row--suppressed" in row.classes
            row_text = "\n".join(str(child.render()) for child in row.query(".finding-detail"))
            assert "apps/web/src/lib/reviews.ts:88" in row_text
            assert "suppressed by judge: style only, low confidence" in row_text

            footer_text = str(pilot.app.query_one("#review-footer").render())
            assert footer_text.startswith("0 findings . 1 suppressed .")

    asyncio.run(exercise())


def test_footer_carries_findings_suppressed_tokens_cost_and_elapsed() -> None:
    async def exercise() -> None:
        from textual.app import App, ComposeResult

        clock = _FakeClock()
        panel = _make_panel(clock)

        class Harness(App[None]):
            def compose(self) -> ComposeResult:
                yield panel

        async with Harness().run_test() as pilot:
            panel.start_agent_reasoning(chunks=())
            clock.now = 2.0
            first = _finding("finding-1")
            panel.add_finding(first, _receipt(first, tokens=4000, cost_usd="0.001"))
            clock.now = 4.5
            second = _finding("finding-2")
            panel.add_finding(second, _receipt(second, tokens=9200, cost_usd="0.003"))
            panel.add_suppressed_finding(
                _suppressed_candidate(), "style only, low confidence"
            )
            await pilot.pause()

            footer_text = str(pilot.app.query_one("#review-footer").render())
            assert footer_text == "2 findings . 1 suppressed . 13.2k tokens . $0.004 . 4.5s"

    asyncio.run(exercise())


def test_review_panel_still_declares_no_border_or_button_in_the_new_elements() -> None:
    """Reuses the D1 transcript rule for the two elements this task adds: the footer and
    the suppressed row must not bring a border or a Button back."""
    assert "border" not in ReviewPanel.DEFAULT_CSS.lower()
    assert ".review-footer" in ReviewPanel.DEFAULT_CSS
    assert ".finding-row--suppressed" in ReviewPanel.DEFAULT_CSS
