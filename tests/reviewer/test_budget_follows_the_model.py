from __future__ import annotations


def test_budget_follows_the_selected_model_window() -> None:
    from pr_reviewer.context_budget import context_budget_for_model

    gpt_4o = context_budget_for_model("gpt-4o")
    gpt_41 = context_budget_for_model("gpt-4.1")
    o3_mini = context_budget_for_model("o3-mini")

    assert gpt_41.tokens > gpt_4o.tokens
    assert o3_mini.tokens < 200_000
