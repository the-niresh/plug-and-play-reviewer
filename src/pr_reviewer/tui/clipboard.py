"""Put text on the real system clipboard, not just the terminal's.

Textual's App.copy_to_clipboard writes the OSC 52 escape sequence, which only lands if
the terminal emulator implements it. macOS Terminal.app does not, and it is the default
terminal on every Mac, so "press c to copy" appeared to work (the TUI said "Link
copied.") and the clipboard stayed empty. tmux and plenty of SSH setups swallow OSC 52
too.

So try the operating system's own clipboard tool first and fall back to OSC 52. The
return value says which happened, so the caller can tell the user the truth instead of
claiming a copy that may not have occurred.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

# First entry that exists on PATH wins. pbcopy ships with macOS; the Linux options cover
# Wayland then X11; clip.exe is reachable from WSL as well as native Windows.
_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "darwin": (("pbcopy",),),
    "win32": (("clip",),),
}
_FALLBACK_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("wl-copy",),
    ("xclip", "-selection", "clipboard"),
    ("xsel", "--clipboard", "--input"),
    ("clip.exe",),
)


def system_clipboard_command() -> tuple[str, ...] | None:
    """The clipboard command for this machine, or None when there is not one."""
    for candidate in _COMMANDS.get(sys.platform, ()) + _FALLBACK_COMMANDS:
        if shutil.which(candidate[0]):
            return candidate
    return None


def copy_to_system_clipboard(text: str) -> bool:
    """True only when a clipboard tool accepted the text. Never raises."""
    command = system_clipboard_command()
    if command is None:
        return False
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell, text on stdin
            command,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0
