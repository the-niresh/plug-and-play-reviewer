"""Dashboard behavior panels (Task 35.E2).

Checks the hosted review dashboard renders how the machine behaved, using the real
field names from the codebase. Never asserts fabricated placeholder numbers.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB_LIB = REPO / "apps" / "web" / "src" / "lib"
PANELS_TS = WEB_LIB / "reviewPanels.ts"
PANELS_COMPONENT = REPO / "apps" / "web" / "src" / "components" / "ReviewBehaviorPanels.tsx"
REVIEW_DETAIL_PAGE = (
    REPO / "apps" / "web" / "src" / "app" / "dashboard" / "reviews" / "[reviewJobId]" / "page.tsx"
)
REQUIRED_LEDGER_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "latency_ms",
    "prompt_cache_hit_rate",
)
REQUIRED_REJECTION_FIELDS = (
    "schema_rejected_findings",
    "grounding_rejected_findings",
    "duplicate_rejected_findings",
)
REQUIRED_OUTCOME_FIELDS = ("suppressed_candidates", "covers_all_changed_files", "omitted_files")
OMISSION_REASONS = (
    "token_budget",
    "patch_omitted_by_github",
    "patch_truncated_by_github",
    "binary",
    "generated",
    "ignored_path",
    "file_size_limit",
    "clone_timeout",
)
PANEL_LABELS = (
    "Tokens",
    "Cost",
    "Latency",
    "Cache hit rate",
    "Retrieval hit rate",
    "Rejected for schema",
    "Rejected for grounding",
    "Rejected for duplication",
    "Suppressed by the judge",
    "Coverage",
    "Omitted files",
    "Budget remaining",
    "Security findings",
    "Eval scores",
    "Multi-model",
)
NO_DATA = "No data yet"


def _run_panel_builder(review: dict[str, object]) -> list[dict[str, str]]:
    script = f"""
import {{ buildReviewPanels }} from "./src/lib/reviewPanels.ts";
const review = {json.dumps(review)};
const panels = buildReviewPanels(review);
for (const panel of panels) {{
  console.log(JSON.stringify({{ label: panel.label, value: panel.value }}));
}}
"""
    completed = subprocess.run(
        ["npx", "tsx", "-e", script],
        cwd=REPO / "apps" / "web",
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_review_panels_module_exists_and_names_real_fields() -> None:
    assert PANELS_TS.is_file(), f"missing {PANELS_TS}"
    text = PANELS_TS.read_text(encoding="utf-8")
    for field in REQUIRED_LEDGER_FIELDS:
        assert field in text, f"reviewPanels.ts must reference ledger field {field}"
    for field in REQUIRED_REJECTION_FIELDS:
        assert field in text, f"reviewPanels.ts must reference rejection field {field}"
    for field in REQUIRED_OUTCOME_FIELDS:
        assert field in text, f"reviewPanels.ts must reference outcome field {field}"
    for reason in OMISSION_REASONS:
        assert reason in text, f"reviewPanels.ts must reference OmissionReason {reason}"
    assert NO_DATA in text


def test_review_behavior_panels_component_exists() -> None:
    assert PANELS_COMPONENT.is_file(), f"missing {PANELS_COMPONENT}"
    text = PANELS_COMPONENT.read_text(encoding="utf-8")
    for label in PANEL_LABELS:
        assert label in text, f"ReviewBehaviorPanels must show panel {label}"


def test_review_detail_page_renders_behavior_panels() -> None:
    text = REVIEW_DETAIL_PAGE.read_text(encoding="utf-8")
    assert "ReviewBehaviorPanels" in text
    assert 'data-testid="review-behavior-panels"' in text


def test_review_detail_page_imports_behavior_panels() -> None:
    text = REVIEW_DETAIL_PAGE.read_text(encoding="utf-8")
    assert 'from "@/components/ReviewBehaviorPanels"' in text


def test_panel_builder_says_no_data_when_metrics_are_missing() -> None:
    panels = _run_panel_builder(
        {
            "review_job_id": "job-1",
            "pull_request_number": 1,
            "head_sha": "abc",
            "status": "completed",
            "stopped_early": False,
            "stopped_early_message": None,
            "created_at": "2026-01-01T00:00:00Z",
            "findings": [],
            "behavior": None,
        }
    )
    latency = next(panel for panel in panels if panel["label"] == "Latency")
    assert latency["value"] == NO_DATA


def test_panel_builder_aggregates_tokens_and_cost_from_receipts() -> None:
    panels = _run_panel_builder(
        {
            "review_job_id": "job-1",
            "pull_request_number": 1,
            "head_sha": "abc",
            "status": "completed",
            "stopped_early": False,
            "stopped_early_message": None,
            "created_at": "2026-01-01T00:00:00Z",
            "findings": [
                {
                    "id": "f-1",
                    "concern": "correctness",
                    "severity": "low",
                    "category": "null-check",
                    "file_path": "src/widget.py",
                    "line_start": 1,
                    "line_end": 1,
                    "title": "Null check",
                    "rationale": "value can be None",
                    "verified": False,
                    "status": "draft",
                    "receipt": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "input_tokens": 120,
                        "output_tokens": 30,
                        "cost_usd": "0.01",
                        "verification_status": "asserted",
                        "verification_reason": None,
                        "sandbox_run_id": None,
                        "command_id": None,
                        "verification_detail": None,
                        "context_sources": [],
                    },
                }
            ],
            "behavior": None,
        }
    )
    tokens = next(panel for panel in panels if panel["label"] == "Tokens")
    cost = next(panel for panel in panels if panel["label"] == "Cost")
    assert tokens["value"] == "150"
    assert cost["value"] == "$0.01"


def test_panel_builder_counts_security_findings() -> None:
    panels = _run_panel_builder(
        {
            "review_job_id": "job-1",
            "pull_request_number": 1,
            "head_sha": "abc",
            "status": "completed",
            "stopped_early": False,
            "stopped_early_message": None,
            "created_at": "2026-01-01T00:00:00Z",
            "findings": [
                {
                    "id": "f-1",
                    "concern": "security",
                    "severity": "high",
                    "category": "auth",
                    "file_path": "src/auth.py",
                    "line_start": 1,
                    "line_end": 1,
                    "title": "Leak",
                    "rationale": "token exposed",
                    "verified": False,
                    "status": "draft",
                    "receipt": None,
                },
                {
                    "id": "f-2",
                    "concern": "correctness",
                    "severity": "low",
                    "category": "logic",
                    "file_path": "src/widget.py",
                    "line_start": 2,
                    "line_end": 2,
                    "title": "Nit",
                    "rationale": "rename",
                    "verified": False,
                    "status": "draft",
                    "receipt": None,
                },
            ],
            "behavior": None,
        }
    )
    security = next(panel for panel in panels if panel["label"] == "Security findings")
    assert security["value"] == "1"
