"""Slack, Discord, Telegram and email senders behind the channel contract (Task 35.E1).

No real network calls. Senders are small POSTs with an injected httpx client.
Imports of new modules stay inside test bodies.
"""

from __future__ import annotations

import json

import httpx
import pytest

from pr_reviewer.contracts.notification import NotificationChannel, NotificationPreview


def _finished_review_preview() -> NotificationPreview:
    return NotificationPreview(
        title="Your pull request was reviewed",
        body="A review finished.",
        confidentiality="ordinary",
    )


def _channel(
    channel_id: str,
    transport: str,
    *,
    purpose: str = "review_ping",
    confidentiality: str = "ordinary",
) -> NotificationChannel:
    return NotificationChannel.model_validate(
        {
            "id": channel_id,
            "transport": transport,
            "purpose": purpose,
            "confidentiality": confidentiality,
        }
    )


def _capture_client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_assert_job_isolation_still_refuses_mixed_ordinary_channel() -> None:
    from pr_reviewer.notifications.channels import ChannelIsolationError, assert_job_isolation

    shared_id = "same-webhook"
    security = _channel(
        shared_id,
        "slack",
        purpose="security_alert",
        confidentiality="ordinary",
    )
    ping = _channel(
        shared_id,
        "slack",
        purpose="review_ping",
        confidentiality="ordinary",
    )
    with pytest.raises(ChannelIsolationError):
        assert_job_isolation([security, ping])


def test_slack_sender_posts_the_finished_review() -> None:
    from pr_reviewer.notifications.senders import ChannelEndpoint, deliver_notifications

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    channel = _channel("slack-ops", "slack")
    endpoint = ChannelEndpoint(
        channel_id="slack-ops",
        slack_webhook_url="https://hooks.slack.com/services/T00/B00/xxx",
    )
    preview = _finished_review_preview()
    result = deliver_notifications(
        preview,
        [channel],
        {endpoint.channel_id: endpoint},
        idempotency_key="job-1:finished",
        client=_capture_client(httpx.MockTransport(handler)),
    )
    assert result.deliveries[0].ok is True
    assert len(captured) == 1
    assert captured[0].url == "https://hooks.slack.com/services/T00/B00/xxx"
    payload = json.loads(captured[0].content.decode())
    assert payload["text"] == f"{preview.title}\n{preview.body}"


def test_discord_sender_posts_the_finished_review() -> None:
    from pr_reviewer.notifications.senders import ChannelEndpoint, deliver_notifications

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(204)

    channel = _channel("discord-ops", "discord")
    endpoint = ChannelEndpoint(
        channel_id="discord-ops",
        discord_webhook_url="https://discord.com/api/webhooks/123/token",
    )
    preview = _finished_review_preview()
    result = deliver_notifications(
        preview,
        [channel],
        {endpoint.channel_id: endpoint},
        idempotency_key="job-1:finished",
        client=_capture_client(httpx.MockTransport(handler)),
    )
    assert result.deliveries[0].ok is True
    assert len(captured) == 1
    payload = json.loads(captured[0].content.decode())
    assert payload["content"] == f"{preview.title}\n{preview.body}"


def test_telegram_sender_posts_the_finished_review() -> None:
    from pr_reviewer.notifications.senders import ChannelEndpoint, deliver_notifications

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    channel = _channel("telegram-ops", "telegram")
    endpoint = ChannelEndpoint(
        channel_id="telegram-ops",
        telegram_bot_token="bot-token",
        telegram_chat_id="chat-99",
    )
    preview = _finished_review_preview()
    result = deliver_notifications(
        preview,
        [channel],
        {endpoint.channel_id: endpoint},
        idempotency_key="job-1:finished",
        client=_capture_client(httpx.MockTransport(handler)),
    )
    assert result.deliveries[0].ok is True
    assert len(captured) == 1
    assert captured[0].url == "https://api.telegram.org/botbot-token/sendMessage"
    payload = json.loads(captured[0].content.decode())
    assert payload["chat_id"] == "chat-99"
    assert payload["text"] == f"{preview.title}\n{preview.body}"


def test_email_sender_posts_the_finished_review_via_resend() -> None:
    from pr_reviewer.notifications.senders import ChannelEndpoint, deliver_notifications

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "email-1"})

    channel = _channel("email-ops", "email")
    endpoint = ChannelEndpoint(
        channel_id="email-ops",
        email_to="auditor@example.com",
        email_from="reviews@example.com",
        resend_api_key="re_test_key",
    )
    preview = _finished_review_preview()
    result = deliver_notifications(
        preview,
        [channel],
        {endpoint.channel_id: endpoint},
        idempotency_key="job-1:finished",
        client=_capture_client(httpx.MockTransport(handler)),
    )
    assert result.deliveries[0].ok is True
    assert len(captured) == 1
    assert captured[0].url == "https://api.resend.com/emails"
    assert captured[0].headers["authorization"] == "Bearer re_test_key"
    payload = json.loads(captured[0].content.decode())
    assert payload["from"] == "reviews@example.com"
    assert payload["to"] == ["auditor@example.com"]
    assert payload["subject"] == preview.title
    assert payload["text"] == preview.body
