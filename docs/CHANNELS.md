# Notification channels

Plug and Play Reviewer can send review notifications to Slack, Discord,
Telegram, and email. Delivery runs on the **local runner**. Webhook URLs, bot
tokens, and email API keys never reach the hosted database.

The live control plane is `https://plugandplayreviewer.online`. The product domain
will be `plugandplayreviewer.online`, but it is not pointed yet.

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

The hosted database migration allows `slack`, `telegram`, and `discord` as
transport values. Email delivery exists in the runner senders but is not yet in
the hosted transport enum. Use Slack, Telegram, or Discord for channels declared
on the hosted plane today.

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

Allowed hosted transports: `slack`, `telegram`, `discord`.
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

## What this doc does not cover

There is no `reviewer setup` flag for notification secrets today. `reviewer
setup` stores the model key only. Channel endpoint wiring is handled inside the
runner delivery path, not through CLI flags documented in `reviewer_entry.py`.

See [SELF_HOSTING.md](SELF_HOSTING.md) for the full runner install flow.
