"""Email sender via Resend HTTP API."""

from __future__ import annotations

import httpx

from pr_reviewer.contracts.notification import NotificationPreview
from pr_reviewer.notifications.dispatch import SendResult

RESEND_URL = "https://api.resend.com/emails"


def send_email_resend(
    preview: NotificationPreview,
    *,
    to_address: str,
    from_address: str,
    api_key: str,
    client: httpx.Client,
) -> SendResult:
    try:
        response = client.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": from_address,
                "to": [to_address],
                "subject": preview.title,
                "text": preview.body,
            },
        )
    except Exception:
        return SendResult(ok=False, error_kind="delivery_failed")
    if response.status_code >= 400:
        return SendResult(ok=False, error_kind="delivery_failed")
    return SendResult(ok=True)
