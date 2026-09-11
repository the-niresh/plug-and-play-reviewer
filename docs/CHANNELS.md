# Notification channels

Plug and Play Reviewer can send review notifications to Slack, Discord,
Telegram, and email. Delivery runs on the **local runner**. Webhook URLs, bot
tokens, and email API keys never reach the hosted database.

The site is `https://plugandplayreviewer.online`; the control plane API is
`https://api.plugandplayreviewer.online`.

## Set one up

Endpoints go into the runner's secret store, the same place as the model key.
Nothing here reaches the hosted database.

```bash
reviewer notify set slack    --slack-webhook https://hooks.slack.com/services/T000/B000/XXXX
reviewer notify set discord  --discord-webhook https://discord.com/api/webhooks/000/XXXX
reviewer notify set telegram --telegram-bot-token 123456:ABC --telegram-chat-id -1001234567890
reviewer notify set email    --email-to you@example.com \
                             --email-from reviewer@yourdomain.com \
                             --resend-key re_xxxxxxxx

reviewer notify list      # which transports are configured, and what a partial one still needs
reviewer notify test      # send a real message to every configured transport
reviewer notify remove slack
```

Every flag for a transport is required. Setting only
`--telegram-bot-token` leaves Telegram listed as `incomplete` and sends nothing,
rather than failing later with `missing_endpoint` at review time.

When a review finds something, each configured transport gets **one** message
naming the pull request and listing the findings. One per review, not one per
finding.

## How the two sides split

| Side | Stores | Does not store |
|---|---|---|
| Hosted control plane | Channel name, transport, purpose, confidentiality, sha256 hash of the endpoint | Webhook URLs, bot tokens, Resend keys |
| Local runner | Actual endpoint secrets in `ChannelEndpoint` | Nothing is sent to Neon except allowlisted job metadata |

The hosted `notification_channels` table accepts `endpoint_hash` as a 64-character
sha256 hex digest of the webhook URL or endpoint material. The URL itself is
never stored and cannot be reversed from the hash.

## Supported transports

These match `src/pr_reviewer/notifications/senders/` and
`ChannelEndpoint` in `endpoints.py`.

### Slack

Uses a Slack incoming webhook URL.

Runner-side fields on `ChannelEndpoint`:

| Field | Required |
|---|---|
| `slack_webhook_url` | yes |

The sender POSTs JSON `{"text": "<title>\n<body>"}` to the webhook URL.

### Discord

Uses a Discord webhook URL.

Runner-side fields:

| Field | Required |
|---|---|
| `discord_webhook_url` | yes |

The sender POSTs JSON `{"content": "<title>\n<body>"}`.

### Telegram

Uses the Telegram Bot API `sendMessage` endpoint.

Runner-side fields:

| Field | Required |
|---|---|
| `telegram_bot_token` | yes |
| `telegram_chat_id` | yes |

The sender POSTs to
`https://api.telegram.org/bot<token>/sendMessage` with `chat_id` and `text`.

### Email (Resend)

Uses the [Resend](https://resend.com) HTTP API at `https://api.resend.com/emails`.

Runner-side fields:

| Field | Required |
|---|---|
| `email_to` | yes |
| `email_from` | yes |
| `resend_api_key` | yes |

The sender POSTs with header `Authorization: Bearer <resend_api_key>` and JSON
`from`, `to`, `subject` (from the preview title), and `text` (from the preview
body).

## Channel metadata

Each notification also carries metadata from `NotificationChannel`:

| Field | Values | Notes |
|---|---|---|
| `transport` | `slack`, `telegram`, `discord`, `email` | Contract and runner senders support all four. |
| `purpose` | `security_alert`, `review_ping` | Which job types may use this channel. |
| `confidentiality` | `restricted`, `ordinary` | Default is `restricted` when unset. Never inferred from transport. |

All four transports are accepted on both sides. The hosted check constraint
was widened to include `email` in migration
`202609120200_notification_channels_email.sql`; before that the contract and the
runner sender both supported email and the hosted table rejected it.

## Routing rules

The notification gate (`notifications/gate.py`) is system-owned. The model
cannot pick a channel or set posting fields. Restricted findings require a
channel declared with `confidentiality: restricted`. A single channel id cannot
mix `security_alert` and `review_ping` purposes in one job batch.

Preview text format for Slack, Discord, and Telegram is:

```
<title>
<body>
```

Email uses the title as the subject and the body as plain text.

## Declaring a channel on the hosted plane

The hosted API stores metadata only. When you declare a channel, pass a sha256
hex digest of the endpoint, not the URL itself:

```python
import hashlib
endpoint_hash = hashlib.sha256(webhook_url.encode("utf-8")).hexdigest()
```

Allowed hosted transports: `slack`, `telegram`, `discord`, `email`.
Allowed purposes: `security_alert`, `review_ping`.
Optional confidentiality: `restricted` (default) or `ordinary`.

## Runner-side endpoint map

At delivery time the runner builds a map of channel id to `ChannelEndpoint`.
Each entry holds the secrets for that transport. Missing or incomplete
endpoints return `missing_endpoint` and do not send.

Example shape (illustrative ids):

```python
from pr_reviewer.notifications.senders import ChannelEndpoint

endpoints = {
    "slack-ops": ChannelEndpoint(
        channel_id="slack-ops",
        slack_webhook_url="https://hooks.slack.com/services/...",
    ),
    "telegram-ops": ChannelEndpoint(
        channel_id="telegram-ops",
        telegram_bot_token="...",
        telegram_chat_id="...",
    ),
}
```

The runner matches hosted channel ids to these local secrets. Webhook URLs and
tokens stay in local storage only.

`reviewer notify` builds this map for you from the secret store. The example
above is the shape it produces; you only need it directly when embedding the
runner in your own code.

## What this doc does not cover

Declaring a channel on the hosted plane is optional and separate. Delivery works
entirely from the runner: the hosted row exists so the control plane can show
that a channel exists, and it holds only a hash of the endpoint, so it can never
be the thing that sends.

See [SELF_HOSTING.md](SELF_HOSTING.md) for the full runner install flow.
