from __future__ import annotations


def test_diff_only_prompt_sets_the_confidence_bar() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT

    prompt = DIFF_ONLY_PROMPT.content.lower()

    assert "thorough on correctness and security" in prompt
    assert "certain before flagging lower-severity" in prompt
    assert "do not speculate" in prompt
    assert "what remains uncertain" in prompt


def test_diff_only_prompt_requires_a_finding_when_the_failure_is_visible_in_the_hunk() -> None:
    # Modeled on flask-py-006 (dev): a one-line local bug. The caller is not needed.
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT

    prompt = DIFF_ONLY_PROMPT.content.lower()
    assert "report it when the failure is visible in the packed hunk" in prompt
    assert "even if the caller is not in the diff" in prompt


def test_diff_only_prompt_frames_the_default_reviewer_as_a_bug_catcher() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT

    prompt = DIFF_ONLY_PROMPT.content.lower()

    assert "bug catcher for a production pull request" in prompt
    assert "not style feedback" in prompt
    assert "auth, data loss, crashes" in prompt
    assert "use included repository context" in prompt
    assert "if no repository context is included" in prompt
