"""reviewer login --no-tui: sign in without the terminal UI.

Signing in used to be the one thing that required the TUI, which made the TUI
compulsory even for people who never wanted it. It also made the sign-in link hard to
get at: inside a full-screen app the link is not ordinary terminal text, so copying it
needs either OSC 52 (which macOS Terminal.app ignores) or a clipboard tool, and opening
it needs browser detection that was wrong on macOS.

Printing the link on its own line removes all of that. Terminal text can be
double-clicked, selected, and copied by the terminal itself, and most terminals make a
bare URL clickable. Nothing here touches the clipboard or guesses at a window server.

The flow is exactly the one ConnectPanel runs: create a pairing code bound to a
sha256 challenge, show the link, wait for the browser half to finish, then exchange the
code for a runner credential using the verifier that only this process ever held.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Sequence

from pr_reviewer.runner.secrets import default_config_dir, get_secret_store
from pr_reviewer.tui.github_connect import (
    HostedOriginError,
    build_github_sign_in_url,
    resolved_hosted_origin,
)
from pr_reviewer.tui.pairing_client import HostedPairingClient
from pr_reviewer.tui.pairing_wait import PairingWaitDeadlineExceeded, wait_for_pairing
from pr_reviewer.tui.screens.connect import sha256_hex

RUNNER_CREDENTIAL_SECRET = "runner_credential"
DEADLINE_SECONDS = 300.0
POLL_INTERVAL_SECONDS = 2.0


def _default_device_name() -> str:
    import socket

    return socket.gethostname() or "reviewer"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="reviewer login --no-tui",
        description="Sign in from a plain terminal. Prints the link instead of opening it.",
        epilog=(
            "exit codes:\n"
            "  0  signed in\n"
            "  1  refused or failed, with the reason on stderr\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--no-tui", action="store_true", help="Accepted and implied here.")
    parser.add_argument(
        "--device-name",
        default=None,
        help="How this machine is labelled in the dashboard. Defaults to the hostname.",
    )
    parsed = parser.parse_args(args)

    try:
        hosted_origin = resolved_hosted_origin()
    except HostedOriginError as exc:
        print(f"reviewer login: could not resolve the hosted origin ({exc})", file=sys.stderr)
        return 1

    device_name = parsed.device_name or _default_device_name()
    # The verifier never leaves this process; only its sha256 goes to the control plane,
    # so a pairing code seen by anyone else cannot be exchanged for a credential.
    verifier = secrets.token_urlsafe(32)
    challenge = sha256_hex(verifier)
    client = HostedPairingClient(hosted_origin)

    try:
        code = client.create_code(device_name, challenge)
    except Exception as exc:  # noqa: BLE001 - report the hosted error, never a traceback
        print(f"reviewer login: could not create a sign-in link ({exc})", file=sys.stderr)
        return 1

    try:
        url = build_github_sign_in_url(hosted_origin, pairing_code=code)
    except HostedOriginError as exc:
        print(f"reviewer login: could not build the sign-in link ({exc})", file=sys.stderr)
        return 1

    # On its own line, with nothing after it, so a double-click selects the whole URL and
    # terminals that linkify URLs can find it.
    print("Open this link to sign in:")
    print()
    print(url)
    print()
    print(f"Pairing code: {code}")
    print("Waiting for you to finish in the browser. Ctrl-C to stop.")
    sys.stdout.flush()

    try:
        wait_for_pairing(
            code=code,
            challenge=challenge,
            status_client=client,
            deadline_seconds=DEADLINE_SECONDS,
            poll_interval_seconds=POLL_INTERVAL_SECONDS,
        )
    except PairingWaitDeadlineExceeded as exc:
        print(f"reviewer login: {exc}", file=sys.stderr)
        print("Run `reviewer login --no-tui` again for a fresh link.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nreviewer login: stopped. Nothing was paired.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"reviewer login: lost contact while waiting ({exc})", file=sys.stderr)
        return 1

    try:
        credential = client.exchange(code, verifier)
    except Exception as exc:  # noqa: BLE001
        # Approval is not sign-in. The credential exchange can still fail after the
        # browser half succeeded, and saying "signed in" before this point would be a lie.
        print(f"reviewer login: pairing approved but the exchange failed ({exc})", file=sys.stderr)
        return 1

    store = get_secret_store(file_fallback_directory=default_config_dir())
    store.set(RUNNER_CREDENTIAL_SECRET, credential)
    print(f"Signed in as {device_name}. Start the runner with `reviewer start`.")
    return 0
