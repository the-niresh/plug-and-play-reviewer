"""Slack incoming webhook sender."""

from __future__ import annotations

import httpx

from pr_reviewer.contracts.notification import NotificationPreview
from pr_reviewer.notifications.dispatch import SendResult
from pr_reviewer.notifications.senders.message import format_notification_text


def send_slack(
    preview: NotificationPreview,
    *,
    webhook_url: str,
    client: httpx.Client,
) -> SendResult:
    try:
        response = client.post(webhook_url, json={"text": format_notification_text(preview)})
    except Exception:
        return SendResult(ok=False, error_kind="delivery_failed")
    if response.status_code >= 400:
        return SendResult(ok=False, error_kind="delivery_failed")
    return SendResult(ok=True)
