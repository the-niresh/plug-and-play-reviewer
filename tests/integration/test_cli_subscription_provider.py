"""CLI subscription provider runs argv commands and preserves local model semantics."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _request() -> object:
    from pr_reviewer.models.provider import ModelRequest, UntrustedInput

    return ModelRequest(
        model="gpt-4o-mini",
        prompt_name="reviewer",
        prompt_version="1",
        prompt_content="review safely",
        schema_name="FindingCandidate",
        untrusted_inputs=[UntrustedInput(name="diff", content="+return items[index]")],
        timeout_seconds=3.0,
        max_output_tokens=128,
    )


def test_cli_subscription_returns_completion_with_cost_and_ledger(tmp_path: Path) -> None:
    from pr_reviewer.models.cli_provider import (
        CliSubscriptionProvider,
        CliSubscriptionProviderConfig,
    )
    from pr_reviewer.models.provider import model_call_ledger_fields

    executable = tmp_path / "fake-cli.py"
    _write_executable(
        executable,
        """#!/usr/bin/env python3
import json
import sys

if any(arg == "gpt-4o-mini" for arg in sys.argv[1:]):
    print('{"error":"model leaked into argv"}', file=sys.stderr)
    raise SystemExit(4)

request = json.load(sys.stdin)
if request.get("model") != "gpt-4o-mini":
    print('{"error":"model missing from stdin payload"}', file=sys.stderr)
    raise SystemExit(5)

response = {
    "content": {
        "concern": "correctness",
        "severity": "low",
        "category": "logic",
        "file_path": "app.py",
        "line_start": 4,
        "line_end": 4,
        "title": "cli path works",
        "rationale": "response returned from fake executable",
        "evidence": ["app.py:4"],
        "confidence": 0.6,
    },
    "input_tokens": 2000,
    "output_tokens": 1000,
    "provider_request_id": "cli-req-1"
}
print(json.dumps(response))
""",
    )

    provider = CliSubscriptionProvider(
        config=CliSubscriptionProviderConfig(
            executable=str(executable),
            argv=("complete", "--json"),
        )
    )
    response = provider.complete_json(_request())
    ledger = model_call_ledger_fields(response)

    assert response.parsed["title"] == "cli path works"
    assert response.provider == "openai"
    assert response.prompt_name == "reviewer"
    assert response.prompt_version == "1"
    assert response.provider_request_id == "cli-req-1"
    assert Decimal(response.cost_usd) == Decimal("0.0009")
    assert ledger["input_tokens"] == 2000
    assert ledger["output_tokens"] == 1000
    assert ledger["cost_usd"] == "0.0009"


def test_cli_subscription_maps_typed_rate_limit_error(tmp_path: Path) -> None:
    from pr_reviewer.models.cli_provider import (
        CliSubscriptionProvider,
        CliSubscriptionProviderConfig,
    )
    from pr_reviewer.models.provider import ModelRateLimit

    executable = tmp_path / "fake-cli-rate-limit.py"
    _write_executable(
        executable,
        """#!/usr/bin/env python3
import json
import sys

json.load(sys.stdin)
print(json.dumps({"error_kind": "rate_limit", "message": "too many requests"}), file=sys.stderr)
raise SystemExit(2)
""",
    )

    provider = CliSubscriptionProvider(
        config=CliSubscriptionProviderConfig(
            executable=str(executable),
            argv=("complete", "--json"),
        )
    )

    with pytest.raises(ModelRateLimit):
        provider.complete_json(_request())
