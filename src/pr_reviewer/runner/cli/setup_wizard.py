"""Sectioned interactive setup for the local reviewer runner."""

from __future__ import annotations

import argparse
import json
import os
import sys
import termios
import tty
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TextIO

from pr_reviewer.models.catalogue import (
    CUSTOM_ENDPOINT_OPTION,
    CUSTOM_MODEL_OPTION,
    default_model_for,
    list_providers,
    models_for,
    provider_for,
)
from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
from pr_reviewer.runner.secrets import SecretStore, default_config_dir
from pr_reviewer.tui.github_connect import DEFAULT_HOSTED_ORIGIN, normalize_hosted_origin

MODEL_KEY_SECRET = "model_key"
SETUP_CONFIG_FILENAME = "setup.json"
RADIO_HEADER = "↑↓ navigate  ENTER/SPACE select  ESC cancel"
SECTION_ORDER = ("location", "provider", "model", "github", "prompt")
SECTION_TITLES = {
    "location": "Configuration Location",
    "provider": "Inference Provider",
    "model": "Model",
    "github": "GitHub",
    "prompt": "Prompt",
}


@dataclass(frozen=True)
class SetupConfig:
    provider_id: str
    model_id: str
    hosted_origin: str
    prompt_name: str
    prompt_version: str
    custom_base_url: str | None
    custom_model_id: str | None


@dataclass(frozen=True)
class SetupPaths:
    config_dir: Path
    secrets_dir: Path
    data_dir: Path


def setup_config_path(config_dir: Path | None = None) -> Path:
    root = config_dir or default_config_dir()
    return root / SETUP_CONFIG_FILENAME


def default_setup_config() -> SetupConfig:
    first = list_providers()[0]
    return SetupConfig(
        provider_id=first.provider_id,
        model_id=default_model_for(first.provider_id),
        hosted_origin=DEFAULT_HOSTED_ORIGIN,
        prompt_name=DIFF_ONLY_PROMPT.name,
        prompt_version=DIFF_ONLY_PROMPT.version,
        custom_base_url=None,
        custom_model_id=None,
    )


def load_setup_config(config_dir: Path | None = None) -> SetupConfig | None:
    path = setup_config_path(config_dir)
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("setup config must be a JSON object")
    return SetupConfig(
        provider_id=str(raw.get("provider_id", default_setup_config().provider_id)),
        model_id=str(raw.get("model_id", default_setup_config().model_id)),
        hosted_origin=str(raw.get("hosted_origin", DEFAULT_HOSTED_ORIGIN)),
        prompt_name=str(raw.get("prompt_name", DIFF_ONLY_PROMPT.name)),
        prompt_version=str(raw.get("prompt_version", DIFF_ONLY_PROMPT.version)),
        custom_base_url=(
            str(raw["custom_base_url"]) if raw.get("custom_base_url") else None
        ),
        custom_model_id=(
            str(raw["custom_model_id"]) if raw.get("custom_model_id") else None
        ),
    )


def save_setup_config(config: SetupConfig, config_dir: Path | None = None) -> None:
    path = setup_config_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider_id": config.provider_id,
        "model_id": config.model_id,
        "hosted_origin": config.hosted_origin,
        "prompt_name": config.prompt_name,
        "prompt_version": config.prompt_version,
        "custom_base_url": config.custom_base_url,
        "custom_model_id": config.custom_model_id,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_setup_paths(config_dir: Path | None = None) -> SetupPaths:
    root = config_dir or default_config_dir()
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        data_dir = Path(xdg) / "pr-reviewer"
    else:
        data_dir = Path.home() / ".local" / "share" / "pr-reviewer"
    return SetupPaths(config_dir=root, secrets_dir=root, data_dir=data_dir)


def mask_secret(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) <= 8:
        return "******** ✓"
    return f"{cleaned[:8]}... ✓"


def _is_tty(stream: IO[str]) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)())


def radio_select(
    title: str,
    *,
    options: Sequence[str],
    labels: Sequence[str] | None = None,
    current: str | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> str:
    if not options:
        raise ValueError("options must not be empty")
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    display = list(labels) if labels is not None else list(options)
    if len(display) != len(options):
        raise ValueError("labels must match options length")
    active = options.index(current) if current in options else 0

    output_stream.write(f"\n{title}\n")
    output_stream.write(f"{RADIO_HEADER}\n")
    for index, label in enumerate(display):
        marker = ">" if index == (options.index(current) if current in options else 0) else " "
        suffix = "  ← currently active" if current is not None and options[index] == current else ""
        output_stream.write(f" {marker} {label}{suffix}\n")
    output_stream.flush()

    if not _is_tty(input_stream):
        if current is not None and current in options:
            return current
        return options[0]

    while True:
        for index, label in enumerate(display):
            marker = ">" if index == active else " "
            suffix = "  ← currently active" if options[index] == current else ""
            output_stream.write(f" {marker} {label}{suffix}\n")
        output_stream.flush()

        fd = input_stream.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                key = input_stream.read(1)
                if key in ("\r", "\n", " "):
                    choice = options[active]
                    output_stream.write("\n")
                    output_stream.flush()
                    return choice
                if key == "\x03":
                    raise SystemExit("setup cancelled")
                if key == "\x1b":
                    rest = input_stream.read(2)
                    if rest == "[A":
                        active = (active - 1) % len(options)
                        break
                    if rest == "[B":
                        active = (active + 1) % len(options)
                        break
                    raise SystemExit("setup cancelled")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        output_stream.write("\033[F" * len(display))
        output_stream.flush()


def prompt_with_default(
    prompt: str,
    *,
    current: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> str:
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    output_stream.write(f"{prompt} [{current}]: ")
    output_stream.flush()
    if not _is_tty(input_stream):
        line = input_stream.readline()
        cleaned = line.strip()
        return cleaned or current
    line = input_stream.readline()
    cleaned = line.strip()
    return cleaned or current


def prompt_secret_action(
    *,
    masked: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> str:
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    output_stream.write(f"Existing key: {masked}\n")
    output_stream.write("[K]eep / [R]eplace / [C]lear (default K): ")
    output_stream.flush()
    if not _is_tty(input_stream):
        return "keep"
    choice = input_stream.readline().strip().lower()
    if choice in {"", "k", "keep"}:
        return "keep"
    if choice in {"r", "replace"}:
        return "replace"
    if choice in {"c", "clear"}:
        return "clear"
    return "keep"


def run_setup_wizard(
    *,
    secrets: SecretStore,
    argv: Sequence[str],
    read_secret: Callable[[str], str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    config_dir: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="reviewer setup")
    parser.add_argument(
        "section",
        nargs="?",
        choices=SECTION_ORDER,
        help="Jump to one setup section.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fill only missing values.",
    )
    parser.add_argument(
        "--hosted-origin",
        default="",
        help="Hosted control plane origin (deprecated: stored in setup.json).",
    )
    parsed = parser.parse_args(list(argv))
    input_stream = stdin if stdin is not None else sys.stdin
    quick = parsed.quick or not _is_tty(input_stream)
    output_stream = stdout if stdout is not None else sys.stdout
    paths = resolve_setup_paths(config_dir)
    config = load_setup_config(paths.config_dir) or default_setup_config()
    if parsed.hosted_origin:
        normalized = normalize_hosted_origin(parsed.hosted_origin)
        config = SetupConfig(
            provider_id=config.provider_id,
            model_id=config.model_id,
            hosted_origin=normalized,
            prompt_name=config.prompt_name,
            prompt_version=config.prompt_version,
            custom_base_url=config.custom_base_url,
            custom_model_id=config.custom_model_id,
        )
    sections = (parsed.section,) if parsed.section else SECTION_ORDER

    for section in sections:
        if section == "location":
            _run_location_section(paths, stdout=output_stream)
            continue
        if section == "provider":
            config = _run_provider_section(
                config,
                quick=quick,
                stdin=input_stream,
                stdout=output_stream,
            )
            continue
        if section == "model":
            config = _run_model_section(
                config,
                quick=quick,
                stdin=input_stream,
                stdout=output_stream,
            )
            continue
        if section == "github":
            config = _run_github_section(
                config,
                quick=quick,
                stdin=input_stream,
                stdout=output_stream,
            )
            continue
        if section == "prompt":
            config = _run_prompt_section(
                config,
                quick=quick,
                stdin=input_stream,
                stdout=output_stream,
            )

    save_setup_config(config, paths.config_dir)
    _sync_hosted_origin_env(config.hosted_origin, paths.config_dir)
    _configure_model_key(
        secrets,
        read_secret=read_secret,
        quick=quick,
        stdin=input_stream,
        stdout=output_stream,
    )
    return 0


def _print_section_header(section: str, stdout: TextIO) -> None:
    stdout.write(f"\n=== {SECTION_TITLES[section]} ===\n")


def _run_location_section(paths: SetupPaths, *, stdout: TextIO) -> None:
    _print_section_header("location", stdout)
    stdout.write(f"Config: {paths.config_dir}\n")
    stdout.write(f"Secrets: {paths.secrets_dir}\n")
    stdout.write(f"Data: {paths.data_dir}\n")


def _run_provider_section(
    config: SetupConfig,
    *,
    quick: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> SetupConfig:
    _print_section_header("provider", stdout)
    if quick and config.provider_id:
        return config
    options = [provider.provider_id for provider in list_providers()]
    labels = [provider.label for provider in list_providers()]
    options.append(CUSTOM_ENDPOINT_OPTION)
    labels.append("Custom endpoint (enter URL manually)")
    current = config.provider_id if config.provider_id in options else options[0]
    chosen = radio_select(
        "Choose an inference provider",
        options=options,
        labels=labels,
        current=current,
        stdin=stdin,
        stdout=stdout,
    )
    if chosen == CUSTOM_ENDPOINT_OPTION:
        custom_url = prompt_with_default(
            "Custom endpoint URL",
            current=config.custom_base_url or "https://",
            stdin=stdin,
            stdout=stdout,
        )
        return SetupConfig(
            provider_id="openai",
            model_id=config.model_id,
            hosted_origin=config.hosted_origin,
            prompt_name=config.prompt_name,
            prompt_version=config.prompt_version,
            custom_base_url=custom_url,
            custom_model_id=config.custom_model_id,
        )
    return SetupConfig(
        provider_id=chosen,
        model_id=default_model_for(chosen),
        hosted_origin=config.hosted_origin,
        prompt_name=config.prompt_name,
        prompt_version=config.prompt_version,
        custom_base_url=None,
        custom_model_id=config.custom_model_id,
    )


def _run_model_section(
    config: SetupConfig,
    *,
    quick: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> SetupConfig:
    _print_section_header("model", stdout)
    if quick and config.model_id:
        return config
    options = [entry.model_id for entry in models_for(config.provider_id)]
    labels = [entry.label for entry in models_for(config.provider_id)]
    options.append(CUSTOM_MODEL_OPTION)
    labels.append("Enter custom model name")
    current = config.model_id if config.model_id in options else options[0]
    chosen = radio_select(
        "Choose a model",
        options=options,
        labels=labels,
        current=current,
        stdin=stdin,
        stdout=stdout,
    )
    if chosen == CUSTOM_MODEL_OPTION:
        custom_model = prompt_with_default(
            "Custom model name",
            current=config.custom_model_id or config.model_id,
            stdin=stdin,
            stdout=stdout,
        )
        return SetupConfig(
            provider_id=config.provider_id,
            model_id=custom_model,
            hosted_origin=config.hosted_origin,
            prompt_name=config.prompt_name,
            prompt_version=config.prompt_version,
            custom_base_url=config.custom_base_url,
            custom_model_id=custom_model,
        )
    return SetupConfig(
        provider_id=config.provider_id,
        model_id=chosen,
        hosted_origin=config.hosted_origin,
        prompt_name=config.prompt_name,
        prompt_version=config.prompt_version,
        custom_base_url=config.custom_base_url,
        custom_model_id=None,
    )


def _run_github_section(
    config: SetupConfig,
    *,
    quick: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> SetupConfig:
    _print_section_header("github", stdout)
    if quick and config.hosted_origin:
        return config
    origin = prompt_with_default(
        "Hosted control plane origin (https://)",
        current=config.hosted_origin,
        stdin=stdin,
        stdout=stdout,
    )
    normalized = normalize_hosted_origin(origin)
    return SetupConfig(
        provider_id=config.provider_id,
        model_id=config.model_id,
        hosted_origin=normalized,
        prompt_name=config.prompt_name,
        prompt_version=config.prompt_version,
        custom_base_url=config.custom_base_url,
        custom_model_id=config.custom_model_id,
    )


def _run_prompt_section(
    config: SetupConfig,
    *,
    quick: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> SetupConfig:
    _print_section_header("prompt", stdout)
    if quick:
        return config
    prompt_name = prompt_with_default(
        "Reviewer prompt name",
        current=config.prompt_name,
        stdin=stdin,
        stdout=stdout,
    )
    prompt_version = prompt_with_default(
        "Reviewer prompt version",
        current=config.prompt_version,
        stdin=stdin,
        stdout=stdout,
    )
    return SetupConfig(
        provider_id=config.provider_id,
        model_id=config.model_id,
        hosted_origin=config.hosted_origin,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        custom_base_url=config.custom_base_url,
        custom_model_id=config.custom_model_id,
    )


def _configure_model_key(
    secrets: SecretStore,
    *,
    read_secret: Callable[[str], str] | None,
    quick: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> None:
    existing = secrets.get(MODEL_KEY_SECRET)
    if quick and existing and existing.strip():
        return
    reader = read_secret
    if reader is None:
        import getpass

        reader = getpass.getpass
    if existing and existing.strip():
        action = prompt_secret_action(masked=mask_secret(existing), stdin=stdin, stdout=stdout)
        if action == "keep":
            return
        if action == "clear":
            secrets.delete(MODEL_KEY_SECRET)
            return
    key = reader("your LLM provider API key")
    if key.strip():
        secrets.set(MODEL_KEY_SECRET, key.strip())


def _sync_hosted_origin_env(hosted_origin: str, config_dir: Path) -> None:
    env_path = config_dir / ".env"
    lines: list[str] = []
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    key = "PR_REVIEWER_HOSTED_ORIGIN"
    replaced = False
    updated: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            updated.append(f"{key}={hosted_origin}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"{key}={hosted_origin}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def effective_base_url(config: SetupConfig) -> str:
    if config.custom_base_url:
        return config.custom_base_url
    return provider_for(config.provider_id).base_url


def effective_model_id(config: SetupConfig) -> str:
    if config.custom_model_id:
        return config.custom_model_id
    return config.model_id
