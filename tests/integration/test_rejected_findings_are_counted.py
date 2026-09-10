from __future__ import annotations

from test_review_pull_request import _draft_dict, _file, _packed, _review


def test_rejected_findings_are_counted_by_failure_kind() -> None:
    packed = _packed([_file("app.py")])

    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(),
                {"title": "not enough fields"},
                _draft_dict(line_start=99, line_end=99, title="outside changed lines"),
                _draft_dict(),
            ]
        },
    )

    assert [item.title for item in outcome.candidates] == ["Missing null check"]
    assert outcome.schema_rejected_findings == 1
    assert outcome.grounding_rejected_findings == 1
    assert outcome.duplicate_rejected_findings == 1
