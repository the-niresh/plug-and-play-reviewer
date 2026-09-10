"""Landing page must show the product, the privacy split, and the engineering work.

These checks fail if the page goes back to a thin three-pillar hero. They look at
the copy and structure, not at whether a function was called.
"""

from __future__ import annotations

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
WEB_SRC = REPO / "apps" / "web" / "src"
LANDING_PAGE = WEB_SRC / "app" / "page.tsx"
LANDING_DIR = WEB_SRC / "components" / "landing"


def landing_source() -> str:
    chunks = [LANDING_PAGE.read_text(encoding="utf-8")]
    if LANDING_DIR.is_dir():
        for path in sorted(LANDING_DIR.rglob("*")):
            if path.suffix in {".ts", ".tsx", ".css"}:
                chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


REQUIRED_HEADINGS = (
    "How a review moves",
    "Hosted vs local",
    "What already works",
    "What teams can change",
    "What stays free and what is for teams",
    "What the evals show",
    "How to set it up",
    "What is not automatic yet",
)

# "model key" was renamed on 2026-09-10: it meant nothing to a reader, who has an OpenAI
# or Anthropic or Groq API key, not a "model key". The claim being guarded is unchanged,
# that the key stays on the runner; only the words a user actually understands changed.
REQUIRED_PRIVACY_CLAIMS = (
    "source",
    "diffs",
    "provider api key",
)

REQUIRED_FLOW_STEPS = (
    "GitHub PR",
    "hosted job",
    "local runner",
    "retrieval",
    "review comment",
)

# "CodeRabbit alternative" was removed on 2026-09-10. The owner chose to frame the landing
# page on mechanism alone, with no competitor named, and a comparison claim is not one we
# have measured: running both tools on the same PRs has not been done. Restore this phrase
# only alongside that head-to-head, published including the cases we lose.
REQUIRED_SEARCH_PHRASES = (
    "AI code review self hosted",
    "open source PR reviewer",
    "private AI code review",
)


def test_landing_page_exists() -> None:
    assert LANDING_PAGE.is_file(), f"missing {LANDING_PAGE}"


def test_landing_has_required_sections() -> None:
    source = landing_source()
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in source]
    assert missing == [], f"landing is missing sections: {missing}"


def test_landing_has_a_hosted_vs_local_table() -> None:
    source = landing_source()
    assert "<table" in source, "privacy model must be a real table, not a stack of cards"
    assert "Hosted" in source
    assert "Local" in source
    for claim in REQUIRED_PRIVACY_CLAIMS:
        assert claim in source.lower() or claim in source


def test_landing_names_the_review_flow() -> None:
    source = landing_source()
    missing = [step for step in REQUIRED_FLOW_STEPS if step not in source]
    assert missing == [], f"review flow is missing steps: {missing}"


def test_landing_states_the_human_gate() -> None:
    source = landing_source()
    assert "human" in source.lower()
    assert "does not post" in source.lower() or "until a human" in source.lower()


def test_landing_names_grounding_suggestions_and_opt_in_specialists() -> None:
    source = landing_source()
    assert "ground" in source.lower()
    assert "suggestion" in source.lower()
    assert "opt-in" in source.lower()
    assert "off by default" in source.lower()


def test_landing_puts_search_phrases_in_real_sentences() -> None:
    source = landing_source()
    missing = [phrase for phrase in REQUIRED_SEARCH_PHRASES if phrase not in source]
    assert missing == [], f"landing is missing search phrases: {missing}"


def test_landing_does_not_call_evals_a_baseline() -> None:
    source = landing_source()
    lowered = source.lower()
    assert "not a baseline" in lowered or "not a published baseline" in lowered
    assert "zod" in lowered
    assert "7" in source or "seven" in lowered
    assert "self-improving" not in lowered


def test_landing_states_free_tier_without_checkout() -> None:
    source = landing_source().lower()
    assert "free tier" in source
    assert "one github user" in source or "one repository" in source
    assert "$" not in source.split("what stays free")[1].split("what the evals")[0]


def test_landing_does_not_use_a_purple_gradient_hero() -> None:
    source = landing_source()
    forbidden = ("purple", "violet", "#7c3aed", "#8b5cf6", "from-purple", "to-violet")
    hits = [token for token in forbidden if token in source.lower()]
    assert hits == [], f"landing uses a purple/violet token: {hits}"
