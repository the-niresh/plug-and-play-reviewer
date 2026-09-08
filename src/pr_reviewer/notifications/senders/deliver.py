"""Route channels through senders and the existing dispatch contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from pr_reviewer.contracts.notification import NotificationChannel, NotificationPreview
from pr_reviewer.notifications.channels import assert_job_isolation
from pr_reviewer.notifications.dispatch import (
    FanOutResult,
    SendFn,
    SendResult,
    dispatch_notifications,
)
from pr_reviewer.notifications.senders.discord import send_discord
from pr_reviewer.notifications.senders.email import send_email_resend
from pr_reviewer.notifications.senders.endpoints import ChannelEndpoint
from pr_reviewer.notifications.senders.slack import send_slack
from pr_reviewer.notifications.senders.telegram import send_telegram


def _missing_endpoint(channel_id: str) -> SendResult:
    return SendResult(ok=False, error_kind="missing_endpoint")


def build_send_fn(
    endpoints: Mapping[str, ChannelEndpoint],
    *,
    client: httpx.Client,
) -> SendFn:
    def send(channel: NotificationChannel, preview: NotificationPreview) -> SendResult:
        endpoint = endpoints.get(channel.id)
        if endpoint is None:
            return _missing_endpoint(channel.id)
        if channel.transport == "slack":
            if not endpoint.slack_webhook_url:
                return _missing_endpoint(channel.id)
            return send_slack(preview, webhook_url=endpoint.slack_webhook_url, client=client)
        if channel.transport == "discord":
            if not endpoint.discord_webhook_url:
                return _missing_endpoint(channel.id)
            return send_discord(preview, webhook_url=endpoint.discord_webhook_url, client=client)
        if channel.transport == "telegram":
            if not endpoint.telegram_bot_token or not endpoint.telegram_chat_id:
                return _missing_endpoint(channel.id)
            return send_telegram(
                preview,
                bot_token=endpoint.telegram_bot_token,
                chat_id=endpoint.telegram_chat_id,
                client=client,
            )
        if channel.transport == "email":
            if not endpoint.email_to or not endpoint.email_from or not endpoint.resend_api_key:
                return _missing_endpoint(channel.id)
            return send_email_resend(
                preview,
                to_address=endpoint.email_to,
                from_address=endpoint.email_from,
                api_key=endpoint.resend_api_key,
                client=client,
            )
        return SendResult(ok=False, error_kind="unknown_transport")

    return send


def deliver_notifications(
    preview: NotificationPreview,
    channels: Sequence[NotificationChannel],
    endpoints: Mapping[str, ChannelEndpoint],
    *,
    idempotency_key: str,
    client: httpx.Client,
    seen_keys: set[tuple[str, str]] | None = None,
) -> FanOutResult:
    assert_job_isolation(channels)
    return dispatch_notifications(
        preview,
        channels,
        build_send_fn(endpoints, client=client),
        idempotency_key=idempotency_key,
        seen_keys=seen_keys,
    )
