"""Budget policy shared by both planes. Unset means deny, not unlimited.

Per-job reservation is executed by local_store.budget against runner SQLite.
Aggregate repository enforcement is executed by control_plane.budget against Neon.
The two stay consistent when the runner is offline mid-job because the hosted
reservation is keyed by job_id and stays held until the job is dead, cancelled,
or committed. Local reservation dies with the process; a recovered runner starts
a new local reservation against the job envelope, not against the repo cap.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

BudgetDeniedReason = Literal["unset", "insufficient"]
ReviewRole = Literal["triage", "generate", "judge", "explore"]


class BudgetDenied(Exception):
    def __init__(self, reason: BudgetDeniedReason) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class BudgetLimit:
    max_tokens: int | None
    max_cost_usd: Decimal | None


def is_configured(limit: BudgetLimit | None) -> bool:
    if limit is None:
        return False
    if limit.max_tokens is None or limit.max_cost_usd is None:
        return False
    return limit.max_tokens > 0 and limit.max_cost_usd > 0


def require_configured(limit: BudgetLimit | None) -> BudgetLimit:
    if not is_configured(limit):
        raise BudgetDenied("unset")
    assert limit is not None
    return limit


@dataclass(frozen=True)
class CostEstimate:
    """What a call is expected to cost before it is made, not after."""

    input_tokens: int
    output_tokens: int
    cost_usd: Decimal

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class ReviewBudgetRefusal:
    """A user-facing review refusal with plain-language next action."""

    code: str
    message: str
    action: str


def exceeds_limit(limit: BudgetLimit, estimate: CostEstimate) -> bool:
    if limit.max_tokens is not None and estimate.total_tokens > limit.max_tokens:
        return True
    return limit.max_cost_usd is not None and estimate.cost_usd > limit.max_cost_usd


def require_within_budget(limit: BudgetLimit | None, estimate: CostEstimate) -> BudgetLimit:
    """Refuse before spending, not after. Unset still means deny, per require_configured."""
    configured = require_configured(limit)
    if exceeds_limit(configured, estimate):
        raise BudgetDenied("insufficient")
    return configured


def monthly_review_cap_refusal(
    *,
    repository: str,
    monthly_cap_usd: Decimal | None,
    monthly_spend_by_repository_role: Mapping[tuple[str, ReviewRole], Decimal],
    estimated_review_cost_usd: Decimal = Decimal("0"),
) -> ReviewBudgetRefusal | None:
    """Return a product-surface refusal when this month's repository cap is reached."""

    if monthly_cap_usd is None or monthly_cap_usd <= 0:
        return ReviewBudgetRefusal(
            code="repository_monthly_cap_unset",
            message=(
                f"Review refused for {repository}. A monthly budget cap is not set, "
                "and reviews are denied until one is configured."
            ),
            action="Set a positive monthly cap for this repository, then retry the review.",
        )

    repository_role_spend: dict[ReviewRole, Decimal] = {}
    repository_spent = Decimal("0")
    for (repo_name, role), cost in monthly_spend_by_repository_role.items():
        if repo_name != repository:
            continue
        normalized_cost = cost if cost > 0 else Decimal("0")
        repository_spent += normalized_cost
        repository_role_spend[role] = (
            repository_role_spend.get(role, Decimal("0")) + normalized_cost
        )

    estimated_cost = estimated_review_cost_usd if estimated_review_cost_usd > 0 else Decimal("0")
    projected_spend = repository_spent + estimated_cost
    if projected_spend < monthly_cap_usd:
        return None

    ordered_role_spend = sorted(
        repository_role_spend.items(),
        key=lambda item: (-item[1], item[0]),
    )
    role_breakdown = ", ".join(
        f"{role}: ${_format_usd(cost)}" for role, cost in ordered_role_spend
    )
    if not role_breakdown:
        role_breakdown = "none recorded"
    return ReviewBudgetRefusal(
        code="repository_monthly_cap_reached",
        message=(
            f"Review refused for {repository}. This month already spent "
            f"${_format_usd(repository_spent)} of the ${_format_usd(monthly_cap_usd)} monthly cap. "
            f"Role spend: {role_breakdown}. "
            f"Starting this review would bring monthly spend to ${_format_usd(projected_spend)}."
        ),
        action="Raise the repository monthly cap or retry after the month resets.",
    )


def _format_usd(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")
