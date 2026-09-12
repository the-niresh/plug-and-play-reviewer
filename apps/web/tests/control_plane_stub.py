"""A stand-in for the hosted control plane, for Playwright only.

Replaces tests/dashboard_api_server.py, which served /dashboard/* -- the shape of an
earlier dashboard that no longer exists. Every /dashboard page now reads through
src/lib/reviews.ts, which fetches CONTROL_PLANE_ORIGIN/api/reviews server-side and
forwards the viewer's own cookie header, so that is what this serves.

Auth is the real rule, not a toggle: src/lib/session.ts treats a non-empty
`gh_live_sign_in` cookie as signed in, and the control plane answers 401 without a valid
session. Both paths matter, because "not signed in", "could not load" and "loaded and
empty" are three separate screens the dashboard is careful to keep distinct.

Standard library only, so it starts in milliseconds and adds no dependency to the web
app's test run.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8742
SIGN_IN_COOKIE = "gh_live_sign_in"

RUNNER_ID = "11111111-2222-3333-4444-555555555555"
DEVICE_NAME = "playwright-runner"
REPOSITORY_NAME = "acme/alpha"
FINDING_TITLE = "Null check on widget.value"
REVIEW_JOB_ID = "job-dash-1"

REVIEWS = {
    "repositories": [
        {
            "installation_id": 7010,
            "github_repository_id": 11,
            "repository_name": REPOSITORY_NAME,
            "reviews": [
                {
                    "review_job_id": REVIEW_JOB_ID,
                    "pull_request_number": 7,
                    "pull_request_url": "https://github.com/acme/alpha/pull/7",
                    "head_sha": "a" * 40,
                    "status": "succeeded",
                    "stopped_early": False,
                    "stopped_early_message": None,
                    "created_at": "2026-09-11T10:00:00Z",
                    "findings": [
                        {
                            "finding_id": "f-dash-1",
                            "title": FINDING_TITLE,
                            "severity": "high",
                            "concern": "correctness",
                            "file_path": "src/widget.py",
                            "line_start": 14,
                            "line_end": 14,
                            "rationale": "widget.value can be None here.",
                        }
                    ],
                }
            ],
        }
    ],
    "runners": [
        {
            "runner_id": RUNNER_ID,
            "device_name": DEVICE_NAME,
            "installation_id": 7010,
            "status": "online",
            "last_heartbeat_at": "2026-09-11T10:05:00Z",
        }
    ],
}

PROFILE = {
    "github_login": "playwright-user",
    "github_user_id": 42,
    "avatar_url": None,
    "installations": [{"installation_id": 7010, "account_login": "acme"}],
}


def _signed_in(cookie_header: str) -> bool:
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == SIGN_IN_COOKIE and value:
            return True
    return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: object) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's own casing
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"status": "ok"})
            return
        if path not in {"/api/reviews", "/api/profile"}:
            self._send(404, {"error": "not_found"})
            return
        if not _signed_in(self.headers.get("cookie", "")):
            self._send(401, {"error": "unauthenticated"})
            return
        self._send(200, REVIEWS if path == "/api/reviews" else PROFILE)

    def log_message(self, *_args: object) -> None:
        """Quiet. Playwright's own output is the thing worth reading."""


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
