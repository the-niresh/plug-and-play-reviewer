from __future__ import annotations


def test_every_catalogue_model_has_a_context_budget() -> None:
    from pr_reviewer.context_budget import context_budget_for_model
    from pr_reviewer.models.catalogue import list_providers

    missing: list[str] = []
    for provider in list_providers():
        for model in provider.models:
            try:
                context_budget_for_model(model.model_id)
            except KeyError:
                missing.append(f"{provider.provider_id}/{model.model_id}")

    assert missing == []
