"""Task 31.2: the public scorecard page reads generated, never-hand-edited artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from pr_reviewer.evals.feature_flags import generate_feature_flags
from pr_reviewer.evals.scorecard import (
    Scorecard,
    is_scorecard_refusal,
    validate_published_scorecard,
)

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "apps" / "web" / "src" / "app" / "scorecard" / "page.tsx"
SCORECARD_JSON = REPO / "docs" / "reports" / "scorecard.json"
FEATURE_FLAGS_JSON = REPO / "docs" / "reports" / "feature_flags.json"


def test_scorecard_json_is_a_valid_published_live_baseline() -> None:
    on_disk = json.loads(SCORECARD_JSON.read_text(encoding="utf-8"))
    scorecard = Scorecard.model_validate(on_disk)
    validate_published_scorecard(scorecard)
    assert not is_scorecard_refusal(scorecard)
    assert scorecard.model == "gpt-4o-mini"
    assert scorecard.measured_at == "2026-09-10"
    assert scorecard.reviewed_pr_count == 7
    assert "zod" in (scorecard.sample_limitation or "").lower()
    assert scorecard.precision_per_finding == 0.6666666666666666
    assert scorecard.recall_per_finding == 0.5714285714285714
    assert scorecard.precision_per_case == 0.5714285714285714
    assert scorecard.recall_per_case == 0.5714285714285714
    assert scorecard.false_findings_per_pr == 0.2857142857142857
    assert scorecard.cost_usd == 0.00460575


def test_feature_flags_json_matches_a_fresh_real_generation() -> None:
    on_disk = json.loads(FEATURE_FLAGS_JSON.read_text(encoding="utf-8"))
    fresh = [flag.model_dump() for flag in generate_feature_flags()]
    assert on_disk == fresh


def test_page_reads_the_generated_files_at_render_time() -> None:
    source = PAGE.read_text(encoding="utf-8")
    assert "docs/reports/scorecard.json" in source
    assert "docs/reports/feature_flags.json" in source
    assert "readFileSync" in source


def test_page_never_hides_a_refusal_behind_a_placeholder() -> None:
    source = PAGE.read_text(encoding="utf-8")
    for placeholder in ("N/A", "TBD", "Coming soon", "--"):
        assert placeholder not in source, f"found placeholder text {placeholder!r} in the page"


def test_page_shows_published_baseline_provenance() -> None:
    source = PAGE.read_text(encoding="utf-8")
    for label in ("Model", "Measured", "Sample"):
        assert label in source, f"scorecard page missing provenance label {label!r}"
