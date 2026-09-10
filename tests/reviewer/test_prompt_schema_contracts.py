"""Every JSON-shaped model prompt must name every required contract field."""

from __future__ import annotations

from pr_reviewer.prompts.schema_contracts import json_prompt_contracts


def test_every_json_prompt_names_every_required_contract_field() -> None:
    for contract in json_prompt_contracts():
        prompt = contract.prompt_text().lower()
        for field_name in contract.item_model.model_fields:
            if field_name in contract.skip_fields:
                continue
            assert field_name in prompt, (
                f"{contract.name} prompt is missing field {field_name!r}"
            )
