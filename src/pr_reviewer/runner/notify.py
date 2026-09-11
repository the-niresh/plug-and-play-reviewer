"""Where a review ping actually goes. Runner-side only.

The senders, the fan-out, the isolation check and the preview builder were all written
and tested, and nothing ever called them: there was no way to say where a notification
should go, so no notification was ever sent. This module is that missing piece.

Endpoints live in the runner's secret store next to the model key, never in the hosted
database. A Slack webhook URL is a bearer credential -- anyone holding it can post into
the channel -- so it belongs on the same side of the trust boundary as a model key. The
hosted `notification_channels` table stores a sha256 of the endpoint and nothing else,
which is why it cannot be the source of truth for delivery.

Every channel declared here is `restricted`. That is the safe default rather than a
placeholder: `dispatch_notifications` refuses to send restricted content to an ordinary
channel, and a user pointing this at their own private Slack has not told us the channel
is safe for public detail.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import httpx

from pr_reviewer.contracts.finding import Finding
from pr_reviewer.contracts.notification import NotificationChannel
from pr_reviewer.notifications.dispatch import FanOutResult
from pr_reviewer.notifications.preview import build_review_summary_preview
from pr_reviewer.notifications.senders import ChannelEndpoint, deliver_notifications
from pr_reviewer.runner.secrets import SecretStore

TRANSPORTS: tuple[str, ...] = ("slack", "discord", "telegram", "email")

# Secret name per transport, in the order `reviewer notify set` asks for them. The
# endpoint fields on ChannelEndpoint carry the same names so the mapping below stays a
# rename away from a typo rather than a lookup table to keep in sync by hand.
SECRET_FIELDS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "slack": (("notify_slack_webhook", "slack_webhook_url"),),
    "discord": (("notify_discord_webhook", "discord_webhook_url"),),
    "telegram": (
        ("notify_telegram_bot_token", "telegram_bot_token"),
        ("notify_telegram_chat_id", "telegram_chat_id"),
    ),
    "email": (
        ("notify_email_to", "email_to"),
        ("notify_email_from", "email_from"),
        ("notify_resend_key", "resend_api_key"),
    ),
}


def configured_transports(secrets: SecretStore) -> tuple[str, ...]:
    """Transports with every secret they need. A half-configured one is not returned.

    Returning a partly-filled transport would hand `deliver_notifications` a channel it
    can only answer `missing_endpoint` to, which reads as a delivery failure rather than
    as "you never finished setting this up".
    """
    ready: list[str] = []
    for transport in TRANSPORTS:
        fields = SECRET_FIELDS[transport]
        if all(secrets.get(secret_name) for secret_name, _ in fields):
            ready.append(transport)
    return tuple(ready)


def missing_secrets(secrets: SecretStore, transport: str) -> tuple[str, ...]:
    """Which secret names a transport still needs. Empty means it is ready."""
    return tuple(
        secret_name
        for secret_name, _ in SECRET_FIELDS.get(transport, ())
        if not secrets.get(secret_name)
    )


def build_channels(
    secrets: SecretStore,
) -> tuple[tuple[NotificationChannel, ...], dict[str, ChannelEndpoint]]:
    channels: list[NotificationChannel] = []
    endpoints: dict[str, ChannelEndpoint] = {}
    for transport in configured_transports(secrets):
        values = {
            field: secrets.get(secret_name)
            for secret_name, field in SECRET_FIELDS[transport]
        }
        channels.append(
            NotificationChannel(
                id=transport,
                transport=transport,  # type: ignore[arg-type]
                purpose="review_ping",
                confidentiality="restricted",
            )
        )
        endpoints[transport] = ChannelEndpoint(channel_id=transport, **values)
    return tuple(channels), endpoints


def notify_review_finished(
    secrets: SecretStore,
    findings: Sequence[Finding],
    *,
    pull_request: str,
    idempotency_key: str,
    client: httpx.Client | None = None,
) -> FanOutResult | None:
    """Ping every configured channel once for this review. None when none are set up.

    One message per review, not per finding: `dispatch_notifications` dedupes on
    (idempotency_key, channel_id), so a per-finding loop under one key would deliver the
    first finding and silently mark the rest duplicates.
    """
    if not findings:
        return None
    channels, endpoints = build_channels(secrets)
    if not channels:
        return None
    preview = build_review_summary_preview(
        findings,
        pull_request=pull_request,
        confidentiality="restricted",
    )
    if client is not None:
        return deliver_notifications(
            preview,
            channels,
            endpoints,
            idempotency_key=idempotency_key,
            client=client,
        )
    with httpx.Client(timeout=10.0) as owned:
        return deliver_notifications(
            preview,
            channels,
            endpoints,
            idempotency_key=idempotency_key,
            client=owned,
        )
