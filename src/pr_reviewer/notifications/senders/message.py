"""Shared message formatting for outbound senders."""

from __future__ import annotations

from pr_reviewer.contracts.notification import NotificationPreview


def format_notification_text(preview: NotificationPreview) -> str:
    return f"{preview.title}\n{preview.body}"
