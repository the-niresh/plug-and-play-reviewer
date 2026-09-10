"""Task 35.B7: monthly repository cap refuses with a plain user message."""

from __future__ import annotations

from decimal import Decimal


def test_review_is_refused_when_repository_monthly_cap_is_reached() -> None:
    from pr_reviewer.reliability.budget import monthly_review_cap_refusal

    refusal = monthly_review_cap_refusal(
        repository="acme/widgets",
        monthly_cap_usd=Decimal("4.00"),
        monthly_spend_by_repository_role={
            ("acme/widgets", "triage"): Decimal("0.20"),
            ("acme/widgets", "generate"): Decimal("0.80"),
            ("acme/widgets", "judge"): Decimal("3.00"),
            ("acme/other", "judge"): Decimal("9.00"),
        },
        estimated_review_cost_usd=Decimal("0.01"),
    )

    assert refusal is not None
    assert refusal.code == "repository_monthly_cap_reached"
    assert "Review refused for acme/widgets." in refusal.message
    assert "already spent $4.00 of the $4.00 monthly cap" in refusal.message
    assert "judge: $3.00" in refusal.message
    assert refusal.action == "Raise the repository monthly cap or retry after the month resets."
