from __future__ import annotations


def test_diff_only_prompt_sets_the_confidence_bar() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT

    prompt = DIFF_ONLY_PROMPT.content.lower()

    assert "thorough on correctness and security" in prompt
    assert "certain before flagging lower-severity" in prompt
    assert "do not speculate" in prompt
    assert "what remains uncertain" in prompt
