"""Task 35.B6: consensus fan-out must not leak worker threads."""

from __future__ import annotations

import threading
import time


def test_consensus_fanout_shuts_down_all_worker_threads() -> None:
    from pr_reviewer.reviewer.consensus import fan_out_generate_findings

    baseline = {
        thread.ident
        for thread in threading.enumerate()
        if thread.name.startswith("pr-reviewer-consensus")
    }

    def generate_one(_model_name: str):
        time.sleep(0.02)
        return ()

    fan_out_generate_findings(
        generate_models=("gpt-4o-mini", "gpt-4.1-mini", "claude-3-5-haiku-latest"),
        generate_one=generate_one,
        max_workers=3,
        future_timeout_seconds=1.0,
    )

    leaked = [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("pr-reviewer-consensus")
        and thread.ident not in baseline
    ]
    assert leaked == []
