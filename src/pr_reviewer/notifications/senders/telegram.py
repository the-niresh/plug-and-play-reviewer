"""Telegram bot sendMessage sender."""

from __future__ import annotations

import httpx

from pr_reviewer.contracts.notification import NotificationPreview
from pr_reviewer.notifications.dispatch import SendResult
from pr_reviewer.notifications.senders.message import format_notification_text


def send_telegram(
    preview: NotificationPreview,
    *,
    bot_token: str,
    chat_id: str,
    client: httpx.Client,
) -> SendResult:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = client.post(
            url,
            json={"chat_id": chat_id, "text": format_notification_text(preview)},
        )
    except Exception:
        return SendResult(ok=False, error_kind="delivery_failed")
    if response.status_code >= 400:
        return SendResult(ok=False, error_kind="delivery_failed")
    return SendResult(ok=True)
