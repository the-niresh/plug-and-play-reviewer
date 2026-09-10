"""reviewer setup. Hidden input only. No hosted-plane secrets."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from pr_reviewer.runner.secrets import SecretStore

_SECRET_FLAGS = (
    "--model-key",
    "--neon",
    "--webhook-secret",
    "--github-app-private-key",
    "--pat",
)


def run_setup(
    *,
    hosted_origin: str = "",
    secrets: SecretStore,
    read_secret: Callable[[str], str] | None = None,
    argv: Sequence[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    config_dir: Path | None = None,
) -> int:
    del hosted_origin
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "setup":
        args = args[1:]
    for flag in _SECRET_FLAGS:
        if flag in args:
            raise SystemExit(f"refusing secret flag {flag}")

    from pr_reviewer.runner.cli.setup_wizard import run_setup_wizard

    return run_setup_wizard(
        secrets=secrets,
        argv=args,
        read_secret=read_secret,
        stdin=stdin,
        stdout=stdout,
        config_dir=config_dir,
    )


def main(argv: Sequence[str] | None = None) -> int:
    return run_setup(
        secrets=_default_secrets(),
        argv=list(sys.argv[1:] if argv is None else argv),
    )


def _default_secrets() -> SecretStore:
    from pr_reviewer.runner.secrets import default_config_dir, get_secret_store

    return get_secret_store(file_fallback_directory=default_config_dir())
