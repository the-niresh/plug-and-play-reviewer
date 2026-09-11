"""reviewer notify: where a review ping goes.

Slack, Discord, Telegram and email delivery were all implemented and unreachable, because
nothing stored an endpoint. This is the operator front end for pr_reviewer.runner.notify.

Endpoints go into the runner's secret store, the same place as the model key, and never
into the hosted database. A webhook URL is a bearer credential: whoever holds it can post
into the channel.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import httpx

from pr_reviewer.contracts.notification import NotificationPreview
from pr_reviewer.notifications.senders import deliver_notifications
from pr_reviewer.runner.notify import (
    SECRET_FIELDS,
    TRANSPORTS,
    build_channels,
    configured_transports,
    missing_secrets,
)
from pr_reviewer.runner.secrets import SecretStore, default_config_dir, get_secret_store

# Each transport's flags, in the order they are asked for. The flag name is the secret
# name with the notify_ prefix dropped and underscores turned into dashes, so a new
# transport needs no second table.
_FLAG_HELP = {
    "notify_slack_webhook": "Slack incoming webhook URL.",
    "notify_discord_webhook": "Discord webhook URL.",
    "notify_telegram_bot_token": "Telegram bot token from @BotFather.",
    "notify_telegram_chat_id": "Telegram chat id to post into.",
    "notify_email_to": "Address that receives the ping.",
    "notify_email_from": "Verified Resend sender address.",
    "notify_resend_key": "Resend API key.",
}


def _flag_for(secret_name: str) -> str:
    return "--" + secret_name.removeprefix("notify_").replace("_", "-")


def _dest_for(secret_name: str) -> str:
    return secret_name.removeprefix("notify_")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewer notify",
        description=(
            "Send a ping to Slack, Discord, Telegram or email when a review "
            "finds something."
        ),
        epilog=(
            "exit codes:\n"
            "  0  done\n"
            "  1  refused, such as a missing flag or an unconfigured transport\n"
            "  2  a test send failed\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("list", help="Show which transports are configured.")

    set_parser = sub.add_parser("set", help="Store the endpoint for one transport.")
    set_parser.add_argument("transport", choices=TRANSPORTS)
    for fields in SECRET_FIELDS.values():
        for secret_name, _field in fields:
            set_parser.add_argument(
                _flag_for(secret_name),
                dest=_dest_for(secret_name),
                help=_FLAG_HELP[secret_name],
            )

    remove_parser = sub.add_parser("remove", help="Forget one transport's endpoint.")
    remove_parser.add_argument("transport", choices=TRANSPORTS)

    sub.add_parser("test", help="Send a test message to every configured transport.")
    return parser


def _do_list(secrets: SecretStore) -> int:
    ready = configured_transports(secrets)
    for transport in TRANSPORTS:
        if transport in ready:
            print(f"{transport}: configured")
            continue
        missing = missing_secrets(secrets, transport)
        if len(missing) == len(SECRET_FIELDS[transport]):
            print(f"{transport}: not set up")
        else:
            flags = ", ".join(_flag_for(name) for name in missing)
            print(f"{transport}: incomplete, still needs {flags}")
    if not ready:
        print(
            "\nNothing is configured, so reviews send no notifications.\n"
            "  reviewer notify set slack --slack-webhook https://hooks.slack.com/...",
            file=sys.stderr,
        )
    return 0


def _do_set(secrets: SecretStore, parsed: argparse.Namespace) -> int:
    transport = str(parsed.transport)
    fields = SECRET_FIELDS[transport]
    given = {
        secret_name: getattr(parsed, _dest_for(secret_name), None) for secret_name, _ in fields
    }
    absent = [name for name, value in given.items() if not value]
    if absent:
        flags = ", ".join(_flag_for(name) for name in absent)
        print(f"reviewer notify set {transport}: missing {flags}", file=sys.stderr)
        return 1
    for secret_name, value in given.items():
        assert value is not None
        secrets.set(secret_name, str(value))
    print(f"{transport}: configured. Run `reviewer notify test` to check it.")
    return 0


def _do_remove(secrets: SecretStore, transport: str) -> int:
    for secret_name, _field in SECRET_FIELDS[transport]:
        secrets.delete(secret_name)
    print(f"{transport}: removed.")
    return 0


def _do_test(secrets: SecretStore) -> int:
    channels, endpoints = build_channels(secrets)
    if not channels:
        print("reviewer notify test: nothing configured", file=sys.stderr)
        return 1
    # Restricted, like a real ping, so this exercises the same refusal rules a review
    # would hit rather than a friendlier path that proves less.
    preview = NotificationPreview(
        title="Plug and Play Reviewer test",
        body="If you can read this, review notifications reach this channel.",
        confidentiality="restricted",
    )
    with httpx.Client(timeout=10.0) as client:
        result = deliver_notifications(
            preview,
            channels,
            endpoints,
            idempotency_key="notify-test",
            client=client,
        )
    failed = False
    for delivery in result.deliveries:
        if delivery.ok:
            print(f"{delivery.channel_id}: sent")
        else:
            failed = True
            print(f"{delivery.channel_id}: {delivery.error_kind}", file=sys.stderr)
    return 2 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parsed = _build_parser().parse_args(args)
    secrets = get_secret_store(file_fallback_directory=default_config_dir())

    if parsed.action == "list":
        return _do_list(secrets)
    if parsed.action == "set":
        return _do_set(secrets, parsed)
    if parsed.action == "remove":
        return _do_remove(secrets, str(parsed.transport))
    return _do_test(secrets)
