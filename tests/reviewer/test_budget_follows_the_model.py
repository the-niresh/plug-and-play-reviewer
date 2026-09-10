from __future__ import annotations


def test_budget_follows_the_selected_model_window() -> None:
    from pr_reviewer.context_budget import context_budget_for_model

    gpt_4o_mini = context_budget_for_model("gpt-4o-mini")
    gpt_41 = context_budget_for_model("gpt-4.1")
    o4_mini = context_budget_for_model("o4-mini")

    assert gpt_41.tokens > gpt_4o_mini.tokens
    assert o4_mini.tokens < 200_000
