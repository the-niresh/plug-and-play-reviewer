"""The root layout must compile a client module on every first page.

Next 15 webpack omits __webpack_require__.n when the first compile is server
components only. DashboardShell then crashes on import Link from next/link
with TypeError: __webpack_require__.n is not a function. A client child in
the root layout keeps that helper in webpack.js for landing, docs, and
scorecard first visits.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAYOUT = REPO / "apps" / "web" / "src" / "app" / "layout.tsx"
CLIENT = REPO / "apps" / "web" / "src" / "components" / "ClientRuntime.tsx"


def test_root_layout_renders_a_client_runtime_child() -> None:
    layout = LAYOUT.read_text(encoding="utf-8")
    assert 'from "@/components/ClientRuntime"' in layout
    assert "<ClientRuntime" in layout


def test_client_runtime_is_a_client_module() -> None:
    source = CLIENT.read_text(encoding="utf-8")
    assert source.lstrip().startswith('"use client"')
    assert 'import Link from "next/link"' in source
    assert "export function ClientRuntime" in source
