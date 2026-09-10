"""Hosted control-plane endpoints must fail closed under a simple server-side rate limit."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pr_reviewer.control_plane.app import app
from pr_reviewer.control_plane.rate_limit import (
    SlidingWindowLimiter,
    install_hosted_rate_limiter,
)

PAIRING_PATH = "/api/runner/pairing-codes"
BODY = {"device_name": "rate-limit-device", "challenge": "pkce-challenge"}


def test_unauthenticated_hosted_route_returns_429_after_the_limit() -> None:
    previous = install_hosted_rate_limiter(SlidingWindowLimiter(max_requests=2, window_seconds=60))
    try:
        client = TestClient(app)
        first = client.post(PAIRING_PATH, json=BODY)
        second = client.post(PAIRING_PATH, json=BODY)
        third = client.post(PAIRING_PATH, json=BODY)
        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        payload = third.json()
        assert payload == {"error": "rate_limited"}
        assert "pkce-challenge" not in third.text
        assert "challenge" not in payload
    finally:
        install_hosted_rate_limiter(previous)


def test_health_is_not_rate_limited() -> None:
    previous = install_hosted_rate_limiter(SlidingWindowLimiter(max_requests=1, window_seconds=60))
    try:
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        first = client.post(PAIRING_PATH, json=BODY)
        limited = client.post(PAIRING_PATH, json=BODY)
        assert first.status_code == 200
        assert limited.status_code == 429
        assert limited.json() == {"error": "rate_limited"}
    finally:
        install_hosted_rate_limiter(previous)


def test_rate_limit_fails_closed_without_leaking_the_internal_error() -> None:
    class BoomLimiter:
        def allow(self, key: str) -> bool:
            raise RuntimeError("secret-token-xyz")

    previous = install_hosted_rate_limiter(BoomLimiter())
    try:
        client = TestClient(app)
        response = client.post(PAIRING_PATH, json=BODY)
        assert response.status_code == 429
        assert response.json() == {"error": "rate_limited"}
        assert "secret-token-xyz" not in response.text
        assert "RuntimeError" not in response.text
    finally:
        install_hosted_rate_limiter(previous)
