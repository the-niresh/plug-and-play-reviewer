"""HTTP surface for hosted GitHub sign-in (Runtime Task 2A).

The binding_secret cookie is the whole reason this task exists as more than a state parameter:
Lax, not Strict, because Strict is not sent on the top-level navigation back from github.com to
this callback, and a cookie that silently never arrives makes every real sign-in look identical to
an attack. Scoped to the callback path only, so nothing else on this host ever sees it, and its
Max-Age matches the state's own expiry so the cookie cannot outlive the row it authenticates.
"""

from __future__ import annotations

import html
from urllib.parse import parse_qsl, urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from pr_reviewer.config import get_settings
from pr_reviewer.contracts.runner import PairingApproved, PairingDenied
from pr_reviewer.control_plane.branded_page import render_page
from pr_reviewer.control_plane.github_auth import (
    AccessDenied,
    LiveInstallationAssertion,
    ReturnToRejected,
    SignInDenied,
    VerifiedGitHubUser,
)
from pr_reviewer.control_plane.github_oauth import (
    ALLOWED_RETURN_TO_PATHS,
    LIVE_SIGN_IN_COOKIE_NAME,
    STATE_TTL_SECONDS,
    begin_sign_in,
    capture_live_assertion,
    complete_sign_in,
    issue_live_sign_in,
    read_live_sign_in,
    verify_installation_access,
)
from pr_reviewer.control_plane.pairing import approve_pairing_by_hash, pending_pairing_device_name
from pr_reviewer.control_plane.repository_policy import hash_runner_credential

router = APIRouter(prefix="/api/auth/github", tags=["github-oauth"])

CALLBACK_PATH = "/api/auth/github/callback"
BINDING_SECRET_COOKIE_NAME = "gh_oauth_binding"
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"


@router.get("/sign-in")
def begin_sign_in_route(
    return_to: str, request: Request, pairing_code: str | None = None
) -> RedirectResponse:
    # Hashed here, at the door: nothing past this point, including the oauth_states row itself,
    # ever holds the plaintext pairing code the TUI put in this link.
    pairing_code_hash = hash_runner_credential(pairing_code) if pairing_code else None
    challenge = begin_sign_in(return_to, pairing_code_hash=pairing_code_hash)
    if isinstance(challenge, ReturnToRejected):
        raise HTTPException(status_code=400, detail=challenge.reason)

    # request.base_url reports http behind Traefik, which terminates TLS and forwards
    # plain HTTP, so GitHub would receive an http redirect_uri that does not match the
    # App's https callback. The hosted origin is the authoritative answer, it is
    # validated as https and non-loopback, and unlike a Host header it cannot be
    # spoofed by the caller.
    origin = get_settings().hosted_origin
    if not origin.startswith("https://"):
        raise HTTPException(status_code=500, detail="hosted_origin_not_configured")
    redirect_uri = origin + CALLBACK_PATH
    query = urlencode(
        {
            "client_id": get_settings().github_oauth_client_id,
            "state": challenge.state,
            "redirect_uri": redirect_uri,
        }
    )
    response = RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{query}", status_code=302)
    response.set_cookie(
        key=BINDING_SECRET_COOKIE_NAME,
        value=challenge.binding_secret,
        max_age=STATE_TTL_SECONDS,
        path=CALLBACK_PATH,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.post("/sign-out")
def sign_out_route() -> JSONResponse:
    """Deletes the live sign-in cookie. There is no server-side session to invalidate --
    LIVE_SIGN_IN_COOKIE_NAME is the whole session, sealed by issue_live_sign_in -- so
    discarding it here is the entire logout.
    """
    response = JSONResponse({"signed_out": True})
    response.delete_cookie(LIVE_SIGN_IN_COOKIE_NAME, path="/")
    return response


# Installing the App sends the user here with a code and an installation_id but no
# state, because that redirect starts at GitHub rather than at our /sign-in. State is
# CSRF protection and is not optional, so the code is still refused. What changes is
# that the person sees a sentence and a link instead of a raw validation dump. The
# durable fix is the App's Setup URL pointing at /sign-in; this is the safety net for
# anyone who reaches the callback cold.
_NO_STATE_PAGE = render_page(
    title="Start sign-in again",
    heading="Start sign-in from the beginning",
    body=(
        "<p>This link is missing the one-time value that proves the sign-in started "
        "here, so it was not accepted. That is expected if you arrived straight from "
        "installing the App.</p>"
        '<form method="get" action="/api/auth/github/sign-in">'
        '<input type="hidden" name="return_to" value="/dashboard">'
        '<button type="submit">Sign in with GitHub</button>'
        "</form>"
    ),
)


# Every reason PairingDenialReason can carry, in words a person waiting in a browser
# understands, without repeating the security reasoning collapsed into "invalid_or_expired_code"
# (see github_auth.PairingDenialReason) -- that reasoning is for callers guessing codes, not for
# a person reading a page after a real attempt.
_PAIRING_DENIED_MESSAGES: dict[str, str] = {
    "invalid_or_expired_code": (
        "The pairing code your terminal is waiting on has expired, was already used, or "
        "was never issued. Go back to the terminal and press Sign in to get a new link."
    ),
    "unknown_installation": (
        "This GitHub App installation is not known here yet. Install the App on GitHub, "
        "then go back to the terminal and press Sign in to get a new link."
    ),
    "revoked_installation": (
        "This GitHub App installation was revoked. Reinstall the App, then go back to the "
        "terminal and press Sign in to get a new link."
    ),
    "repository_not_in_installation": (
        "One of the repositories this pairing needs is not covered by this GitHub App "
        "installation. Go back to the terminal and press Sign in to get a new link."
    ),
    # These two are limits, not accidents. Telling someone to sign in again would send
    # them round the same loop forever, which is what the generic message used to do.
    "free_tier_one_repository": (
        "The free tier covers one repository per installation, and this installation "
        "already has one. Pick that same repository, or remove the other one from the "
        "GitHub App installation first."
    ),
    "free_tier_one_user": (
        "The free tier covers one active runner per installation, and one is already "
        "paired. Revoke the existing runner before pairing this terminal. If it is a "
        "machine you no longer use, an owner can revoke it by running "
        "scripts/revoke_runner.py against the database."
    ),
}


def _pairing_denied_page(reason: str) -> HTMLResponse:
    message = html.escape(
        _PAIRING_DENIED_MESSAGES.get(
            reason,
            "Sign-in worked, but pairing did not complete. Go back to the terminal and "
            "press Sign in to get a new link.",
        )
    )
    return HTMLResponse(
        render_page(
            title="Pairing not completed",
            heading="Sign-in worked, but pairing did not complete",
            body=f'<p class="lead">{message}</p>',
        )
    )


def _pairing_approved_page(return_to: str) -> HTMLResponse:
    # Meta-refresh, not JS: this must still redirect even under a strict CSP with no
    # script-src for inline scripts, and the person only needs to see this once, not
    # interact with it.
    destination = html.escape(return_to, quote=True)
    return HTMLResponse(
        render_page(
            title="Terminal signed in",
            heading="Your terminal is signed in",
            head=f'<meta http-equiv="refresh" content="5;url={destination}">',
            body=(
                '<p class="lead">The runner waiting in your terminal is now paired with '
                "this GitHub App installation. Go back to it, or wait a moment to "
                "continue here.</p>"
                f'<p class="quiet"><a href="{destination}">Continue now</a></p>'
            ),
        )
    )


def _pairing_confirm_page(pairing_code_hash: str, device_name: str, return_to: str) -> HTMLResponse:
    """Shown instead of silently granting access: a pairing code was waiting on this exact
    sign-in, but granting it is a decision only the person in the browser can make, not something
    completing GitHub OAuth implies by itself. Without this step, anyone who can get a victim to
    click a "sign in" link carrying an attacker's own pairing code -- e.g. by emailing it, the way
    device-code phishing works against RFC 8628 flows -- would silently bind their own terminal to
    the victim's repositories the moment the victim signed in normally. Requiring an explicit,
    named "Approve" click here is the same mitigation GitHub's own device flow uses.
    """
    device = html.escape(device_name)
    destination = html.escape(return_to, quote=True)
    code_hash = html.escape(pairing_code_hash, quote=True)
    return HTMLResponse(
        render_page(
            title="Approve this device?",
            heading="A terminal wants to pair as you",
            body=(
                f'<p class="lead">A device named <strong>{device}</strong> is waiting to '
                "pair with your GitHub account.</p>"
                "<p>Only approve this if you started that sign-in yourself, from that "
                "terminal. Approving lets it read the repositories this installation "
                "covers.</p>"
                '<form method="post" action="/api/auth/github/approve-pairing">'
                f'<input type="hidden" name="pairing_code_hash" value="{code_hash}">'
                f'<input type="hidden" name="return_to" value="{destination}">'
                f'<button type="submit">Approve &ldquo;{device}&rdquo;</button>'
                "</form>"
                f'<p class="quiet"><a href="{destination}">Cancel, do not pair this '
                "device</a></p>"
            ),
        )
    )


def _auto_approve_waiting_pairing(
    pairing_code_hash: str,
    user: VerifiedGitHubUser | None,
    assertion: LiveInstallationAssertion,
) -> PairingApproved | PairingDenied | None:
    """Link the terminal's waiting pairing to the installation this sign-in just proved control
    of, the same way the manual /dashboard approval flow already does (control_plane/pairing.py's
    approve_pairing). Returns None, rather than a denial, when there is nothing safe to decide
    automatically: with zero installations there is nothing to grant, and with more than one,
    guessing which the terminal should get would be a silent cross-account grant. Either way the
    existing manual approval on /dashboard still works; this is strictly an added shortcut for
    the common single-installation case.
    """
    if len(assertion.installations) != 1:
        return None
    installation_id = next(iter(assertion.installations))
    access = verify_installation_access(user, installation_id, assertion=assertion)
    if isinstance(access, AccessDenied):
        return None
    return approve_pairing_by_hash(pairing_code_hash, access, list(access.repositories))


# response_model=None: the union return is a deliberate two-outcome signature, and
# FastAPI would otherwise try to build a Pydantic model from a Response type.
@router.get("/callback", response_model=None)
def callback_route(
    code: str, request: Request, state: str | None = None
) -> RedirectResponse | HTMLResponse:
    if state is None:
        return HTMLResponse(_NO_STATE_PAGE, status_code=400)
    binding_secret = request.cookies.get(BINDING_SECRET_COOKIE_NAME, "")
    result = complete_sign_in(code, state, binding_secret)
    if isinstance(result, SignInDenied):
        raise HTTPException(status_code=401, detail=result.reason)
    user, pairing_code_hash = result

    assertion = capture_live_assertion(user)

    response: RedirectResponse | HTMLResponse
    if pairing_code_hash is not None and len(assertion.installations) == 1:
        # Single-installation is the only case an automatic grant is even on the table (see
        # _auto_approve_waiting_pairing's own docstring); this is a read-only lookup, so nothing
        # is granted yet, only whether there is still something waiting worth asking about.
        device_name = pending_pairing_device_name(pairing_code_hash)
        if device_name is None:
            response = _pairing_denied_page("invalid_or_expired_code")
        else:
            # Granting happens only from the /approve-pairing POST below, after a person reads
            # the device name and clicks Approve -- see that route and _pairing_confirm_page for
            # why completing GitHub sign-in must never be enough by itself.
            response = _pairing_confirm_page(pairing_code_hash, device_name, user.return_to)
    else:
        response = RedirectResponse(url=user.return_to, status_code=302)

    response.delete_cookie(BINDING_SECRET_COOKIE_NAME, path=CALLBACK_PATH)
    response.set_cookie(
        key=LIVE_SIGN_IN_COOKIE_NAME,
        value=issue_live_sign_in(assertion),
        max_age=STATE_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.post("/approve-pairing")
async def approve_pairing_confirmation_route(request: Request) -> HTMLResponse:
    """The only place a pairing code waiting on a GitHub sign-in actually gets granted. Gated on
    the live-sign-in cookie /callback just set, which SameSite=Lax excludes from a cross-site POST
    (only "safe" top-level navigations carry a Lax cookie cross-site, never a form POST), so a
    phishing page cannot auto-submit this on a victim's behalf -- it can only be reached by the
    same browser that completed GitHub sign-in, clicking the button _pairing_confirm_page showed.

    Parsed by hand with parse_qsl rather than FastAPI's Form(...): the form's two fields are a
    plain application/x-www-form-urlencoded body (the browser's default, no enctype set on
    _pairing_confirm_page's form), and Form(...) would pull in python-multipart for that alone.
    """
    body = (await request.body()).decode("utf-8")
    fields = dict(parse_qsl(body))
    pairing_code_hash = fields.get("pairing_code_hash", "")
    return_to = fields.get("return_to", "")
    if return_to not in ALLOWED_RETURN_TO_PATHS:
        raise HTTPException(status_code=400, detail="return_to_not_allowed")
    assertion = read_live_sign_in(request.cookies.get(LIVE_SIGN_IN_COOKIE_NAME, ""))
    if assertion is None:
        raise HTTPException(status_code=401, detail="missing_sign_in")

    outcome = _auto_approve_waiting_pairing(pairing_code_hash, None, assertion)
    if isinstance(outcome, PairingDenied):
        return _pairing_denied_page(outcome.reason)
    if isinstance(outcome, PairingApproved):
        return _pairing_approved_page(return_to)
    # None: the ambiguous-installation or access-denied case. The confirm page was only ever
    # shown for a single, just-verified installation, so reaching this means something changed
    # (e.g. the installation was revoked) between the callback and this click.
    return _pairing_denied_page("unknown_installation")
