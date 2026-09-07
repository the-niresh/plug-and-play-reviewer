"""Budget policy shared by both planes. Unset means deny, not unlimited.

Per-job reservation is executed by local_store.budget against runner SQLite.
Aggregate repository enforcement is executed by control_plane.budget against Neon.
The two stay consistent when the runner is offline mid-job because the hosted
reservation is keyed by job_id and stays held until the job is dead, cancelled,
or committed. Local reservation dies with the process; a recovered runner starts
a new local reservation against the job envelope, not against the repo cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

BudgetDeniedReason = Literal["unset", "insufficient"]


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
