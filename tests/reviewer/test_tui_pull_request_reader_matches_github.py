"""The TUI's pull request adapter must be callable against the real GitHub function.

This path never worked. The adapter was handed an owner and a repository name and passed
both positionally into github.open_pull_requests.list_open_pull_requests, which takes one
positional repository id and a keyword-only installation id. Every attempt to open a
repository in the terminal died with "takes 1 positional argument but 2 were given", and
no test caught it because the fake reader accepted whatever it was given.
"""

from __future__ import annotations

import inspect
from typing import Any

from pr_reviewer.github import open_pull_requests as real_module
from pr_reviewer.tui.github_reads import (
    FakeOpenPullRequestsReader,
    OpenPullRequestsReader,
    _RealOpenPullRequestsReader,
)


class _RecordingModule:
    """Stands in for the github module but keeps the real signature, so a call that the
    real function would reject is rejected here too."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def list_open_pull_requests(self, *args: Any, **kwargs: Any) -> list[Any]:
        inspect.signature(real_module.list_open_pull_requests).bind(*args, **kwargs)
        self.calls.append((args, kwargs))
        return []


def test_the_adapter_calls_github_the_way_github_expects() -> None:
    module = _RecordingModule()
    reader = _RealOpenPullRequestsReader(module, lambda installation_id: "token")

    reader.list_open_pull_requests(1346610490, 158479604)

    (args, kwargs) = module.calls[0]
    assert args == (1346610490,)
    assert kwargs["installation_id"] == 158479604
    assert callable(kwargs["token_provider"])


def test_the_fake_reader_has_the_same_signature_as_the_real_one() -> None:
    """A fake that accepts anything is how the bug above survived."""
    real = inspect.signature(_RealOpenPullRequestsReader.list_open_pull_requests)
    fake = inspect.signature(FakeOpenPullRequestsReader.list_open_pull_requests)
    protocol = inspect.signature(OpenPullRequestsReader.list_open_pull_requests)

    assert list(real.parameters) == list(fake.parameters) == list(protocol.parameters)
