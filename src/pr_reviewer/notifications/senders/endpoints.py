"""Runner-side delivery targets. Webhook URLs and API keys never leave the runner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelEndpoint:
    channel_id: str
    slack_webhook_url: str | None = None
    discord_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    email_to: str | None = None
    email_from: str | None = None
    resend_api_key: str | None = None
