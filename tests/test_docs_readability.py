"""Docs and landing copy must read plainly (Task 35.E3).

Short sentences. Everyday words. No marketing buzzwords. The checker here is the gate:
it must fail a deliberately florid sentence, and it must pass the real page copy.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WEB_APP = REPO / "apps" / "web" / "src" / "app"

LANDING_PAGE = WEB_APP / "page.tsx"
SITE_NAV = REPO / "apps" / "web" / "src" / "components" / "SiteNav.tsx"
DOCS_PAGE = WEB_APP / "docs" / "page.tsx"
DOCS_AGENTS_PAGE = WEB_APP / "docs" / "agents" / "page.tsx"
DASHBOARD_PAGE = WEB_APP / "dashboard" / "page.tsx"
PROFILE_PAGE = WEB_APP / "dashboard" / "profile" / "page.tsx"
SETTINGS_PAGE = WEB_APP / "dashboard" / "settings" / "page.tsx"

READABILITY_PAGES = (
    LANDING_PAGE,
    DOCS_PAGE,
    DOCS_AGENTS_PAGE,
    SETTINGS_PAGE,
    PROFILE_PAGE,
)

MAX_WORDS_PER_SENTENCE = 28

BANNED_MARKETING_WORDS = (
    "leverage",
    "seamless",
    "revolutionary",
    "cutting-edge",
    "empower",
    "streamline",
    "unlock",
    "transformative",
    "world-class",
    "innovative",
    "synergy",
    "holistic",
    "best-in-class",
    "game-changing",
    "next-generation",
    "frictionless",
    "unparalleled",
    "pioneering",
    "state-of-the-art",
    "ecosystem",
    "delight",
    "robust",
)

FLORID_SENTENCE = (
    "Our revolutionary platform seamlessly empowers teams to unlock unparalleled synergies "
    "through cutting-edge transformative innovation that delights every stakeholder."
)

PROSE_FIELD_RE = re.compile(
    r"(?:body|title|hint|description|label|tag):\s*\"([^\"]+)\"",
    re.MULTILINE,
)
JSX_TEXT_RE = re.compile(r">([^<>{}\n][^<>{}]*?)<")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = SENTENCE_SPLIT_RE.split(cleaned)
    return [part.strip() for part in parts if part.strip()]


def word_count(sentence: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", sentence))


def readability_violations(sentences: list[str]) -> list[str]:
    violations: list[str] = []
    for sentence in sentences:
        count = word_count(sentence)
        if count > MAX_WORDS_PER_SENTENCE:
            violations.append(f"sentence has {count} words (max {MAX_WORDS_PER_SENTENCE}): {sentence}")
        lowered = sentence.lower()
        for word in BANNED_MARKETING_WORDS:
            if word in lowered:
                violations.append(f"banned marketing word '{word}' in: {sentence}")
    return violations


SKIP_PROSE_TOKENS = (
    "className",
    "http://",
    "https://",
    "${",
    "review.",
    "finding.",
    "/dashboard",
    "//",
    "bg-",
    "hover:",
    "focus-visible",
    "text-primary",
    "rounded-",
    "aria-",
    "export ",
    "import ",
    "return ",
    "const ",
)


def _looks_like_user_prose(text: str) -> bool:
    if len(text) < 12:
        return False
    if any(token in text for token in SKIP_PROSE_TOKENS):
        return False
    if text.startswith("@/") or text.endswith(".tsx"):
        return False
    if not any(ch.isalpha() for ch in text):
        return False
    punct = set(".,;:!?'\"")
    readable = sum(ch.isalpha() or ch.isspace() or ch in punct for ch in text)
    return readable / len(text) > 0.75


def prose_strings_from_tsx(source: str) -> list[str]:
    strings = [match.group(1) for match in PROSE_FIELD_RE.finditer(source)]
    for match in re.finditer(r'"([^"\\]{12,})"', source):
        text = match.group(1)
        if _looks_like_user_prose(text):
            strings.append(text)
    for match in JSX_TEXT_RE.finditer(source):
        text = match.group(1).strip()
        if _looks_like_user_prose(text):
            strings.append(text)
    return strings


def test_florid_sentence_fails_the_readability_gate() -> None:
    violations = readability_violations(split_sentences(FLORID_SENTENCE))
    assert violations, "the florid sentence must fail sentence length or banned-word checks"


def test_readability_gate_catches_long_sentences() -> None:
    long_sentence = " ".join(["word"] * (MAX_WORDS_PER_SENTENCE + 1)) + "."
    violations = readability_violations(split_sentences(long_sentence))
    assert any("words" in item for item in violations)


def test_required_routes_exist() -> None:
    for path in (
        LANDING_PAGE,
        DOCS_PAGE,
        DASHBOARD_PAGE,
        PROFILE_PAGE,
        SETTINGS_PAGE,
    ):
        assert path.is_file(), f"missing route file {path}"


def test_landing_page_has_a_deploy_button() -> None:
    source = LANDING_PAGE.read_text(encoding="utf-8")
    assert "Deploy on Render" in source
    assert "render.com/deploy" in source


def test_landing_page_links_to_docs_and_dashboard() -> None:
    landing = LANDING_PAGE.read_text(encoding="utf-8")
    nav = SITE_NAV.read_text(encoding="utf-8")
    assert "SiteNav" in landing
    assert '"/docs"' in nav
    assert '"/dashboard"' in nav


def test_docs_pages_pass_the_readability_gate() -> None:
    offenders: list[str] = []
    for path in READABILITY_PAGES:
        strings = prose_strings_from_tsx(path.read_text(encoding="utf-8"))
        for prose in strings:
            violations = readability_violations(split_sentences(prose))
            for violation in violations:
                offenders.append(f"{path.relative_to(REPO)}: {violation}")
    assert offenders == [], "readability violations:\n" + "\n".join(offenders)
