"""Review notifications reach a channel the user configured.

Every piece of this existed before: senders, fan-out, isolation, preview. Nothing called
any of it and nothing stored an endpoint, so no notification was ever sent. These tests
cover the join: secret store -> channels -> delivery, and the rules that must survive it.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from pr_reviewer.contracts.finding import Finding


class _MemorySecrets:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = dict(values or {})

    def set(self, name: str, value: str) -> None:
        self._values[name] = value

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def delete(self, name: str) -> None:
        self._values.pop(name, None)


def _finding(title: str = "Unchecked index", concern: str = "correctness") -> Finding:
    return Finding.model_validate(
        {
            "id": "f1",
            "review_job_id": "job-1",
            "concern": concern,
            "severity": "high",
            "category": "logic",
            "file_path": "src/app.py",
            "line_start": 12,
            "line_end": 12,
            "title": title,
            "rationale": "The loop can read past the end.",
            "evidence": ["src/app.py:12"],
            "confidence": 0.9,
            "verified": False,
            "verification_method": "not_applicable",
            "public_safe": True,
            "status": "draft",
        }
    )


def test_a_half_configured_transport_is_not_offered() -> None:
    from pr_reviewer.runner.notify import configured_transports, missing_secrets

    secrets = _MemorySecrets({"notify_telegram_bot_token": "123:abc"})

    assert configured_transports(secrets) == ()
    assert missing_secrets(secrets, "telegram") == ("notify_telegram_chat_id",)


def test_configured_transports_become_restricted_channels() -> None:
    from pr_reviewer.runner.notify import build_channels

    secrets = _MemorySecrets(
        {
            "notify_slack_webhook": "https://hooks.slack.com/services/T/B/x",
            "notify_telegram_bot_token": "123:abc",
            "notify_telegram_chat_id": "-100999",
        }
    )

    channels, endpoints = build_channels(secrets)

    assert {channel.id for channel in channels} == {"slack", "telegram"}
    # Restricted is the safe default, not a placeholder: dispatch refuses to send
    # restricted content to an ordinary channel, and nobody told us this one is safe.
    assert all(channel.confidentiality == "restricted" for channel in channels)
    assert all(channel.purpose == "review_ping" for channel in channels)
    assert endpoints["slack"].slack_webhook_url == "https://hooks.slack.com/services/T/B/x"
    assert endpoints["telegram"].telegram_chat_id == "-100999"


def test_review_with_findings_pings_the_configured_channel() -> None:
    from pr_reviewer.runner.notify import notify_review_finished

    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content.decode()))
        return httpx.Response(200, text="ok")

    secrets = _MemorySecrets({"notify_slack_webhook": "https://hooks.slack.com/services/T/B/x"})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = notify_review_finished(
            secrets,
            [_finding(), _finding("Missing test", concern="tests")],
            pull_request="acme/alpha#7",
            idempotency_key="job-1:abc",
            client=client,
        )

    assert result is not None
    assert [delivery.ok for delivery in result.deliveries] == [True]
    # One message for the whole review. dispatch dedupes on (key, channel), so a
    # per-finding loop under one key would deliver the first and drop the rest.
    assert len(sent) == 1
    assert "acme/alpha#7" in json.dumps(sent[0])


def test_nothing_configured_sends_nothing_and_is_not_an_error() -> None:
    from pr_reviewer.runner.notify import notify_review_finished

    assert (
        notify_review_finished(
            _MemorySecrets(),
            [_finding()],
            pull_request="acme/alpha#7",
            idempotency_key="job-1:abc",
        )
        is None
    )


def test_a_review_with_no_findings_sends_nothing() -> None:
    from pr_reviewer.runner.notify import notify_review_finished

    secrets = _MemorySecrets({"notify_slack_webhook": "https://hooks.slack.com/services/T/B/x"})

    assert (
        notify_review_finished(
            secrets,
            [],
            pull_request="acme/alpha#7",
            idempotency_key="job-1:abc",
        )
        is None
    )


def test_restricted_summary_title_does_not_name_a_finding() -> None:
    from pr_reviewer.notifications.preview import build_review_summary_preview

    preview = build_review_summary_preview(
        [_finding(title="Hardcoded admin password")],
        pull_request="acme/alpha#7",
        confidentiality="restricted",
    )

    # The title is what a popup shows on a screen someone else can see.
    assert "Hardcoded admin password" not in preview.title
    assert "Hardcoded admin password" in preview.body
    assert "acme/alpha#7" in preview.title


def test_email_is_a_transport_the_control_plane_accepts() -> None:
    """TransportName listed 'email' and the hosted check constraint rejected it."""
    from typing import get_args

    from pr_reviewer.contracts.notification import TransportName
    from pr_reviewer.control_plane.notification_channels import _TRANSPORTS

    assert set(get_args(TransportName)) == _TRANSPORTS


def test_notify_cli_reports_an_incomplete_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pr_reviewer.runner.cli.notify import main

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert main(["set", "telegram", "--telegram-bot-token", "123:abc"]) == 1
    assert "--telegram-chat-id" in capsys.readouterr().err
