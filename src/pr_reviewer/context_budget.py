"""Token windows for packing. This module must not import settings or secrets."""

from __future__ import annotations

from pr_reviewer.contracts.review_context import ContextBudget

# (context_window, output_allowance). The packer only ever sees window minus allowance.
MODEL_CONTEXT_WINDOWS: dict[str, tuple[int, int]] = {
    "gpt-4o-mini": (128_000, 16_384),
    "gpt-4.1-mini": (1_047_576, 32_768),
    "gpt-4.1": (1_047_576, 32_768),
    "gpt-4.1-nano": (1_047_576, 32_768),
    "o4-mini": (200_000, 100_000),
    "claude-haiku-4-5-20251001": (200_000, 64_000),
    "claude-sonnet-4-20250514": (200_000, 64_000),
    "claude-opus-4-20250514": (200_000, 64_000),
    "claude-3-7-sonnet-latest": (200_000, 64_000),
    "claude-3-5-haiku-latest": (200_000, 8_192),
    "moonshot-v1-8k": (8_000, 4_096),
    "moonshot-v1-32k": (32_000, 8_192),
    "moonshot-v1-128k": (128_000, 8_192),
    "kimi-k2-0711-preview": (128_000, 8_192),
    "kimi-k2-turbo-preview": (128_000, 8_192),
    "qwen-plus": (131_072, 8_192),
    "qwen-turbo": (131_072, 8_192),
    "qwen-max": (131_072, 8_192),
    "qwen2.5-72b-instruct": (131_072, 8_192),
    "qwen2.5-32b-instruct": (131_072, 8_192),
    "openai/gpt-4o-mini": (128_000, 16_384),
    "anthropic/claude-sonnet-4": (200_000, 64_000),
    "google/gemini-2.5-pro": (1_048_576, 65_536),
    "meta-llama/llama-3.3-70b-instruct": (131_072, 8_192),
    "deepseek/deepseek-chat": (64_000, 8_192),
    "llama-3.3-70b-versatile": (131_072, 8_192),
    "llama-3.1-8b-instant": (131_072, 8_192),
    "mixtral-8x7b-32768": (32_768, 8_192),
    "gemma2-9b-it": (8_192, 4_096),
    "llama-guard-3-8b": (8_192, 4_096),
    "grok-3": (131_072, 8_192),
    "grok-3-mini": (131_072, 8_192),
    "grok-2-1212": (131_072, 8_192),
    "grok-2-vision-1212": (32_768, 8_192),
    "grok-beta": (131_072, 8_192),
    "deepseek-chat": (64_000, 8_192),
    "deepseek-reasoner": (64_000, 8_192),
    "deepseek-coder": (64_000, 8_192),
    "deepseek-v3": (64_000, 8_192),
    "deepseek-r1": (64_000, 8_192),
    "gpt-4o": (128_000, 16_384),
    "claude-sonnet-4": (200_000, 64_000),
    "o1": (200_000, 100_000),
    "llama3.3": (131_072, 8_192),
    "qwen2.5": (131_072, 8_192),
    "mistral": (32_768, 8_192),
    "codellama": (16_384, 4_096),
    "gemma2": (8_192, 4_096),
    "opencode-default": (128_000, 8_192),
    "opencode-fast": (128_000, 8_192),
    "opencode-balanced": (128_000, 8_192),
    "opencode-quality": (128_000, 8_192),
    "opencode-coder": (128_000, 8_192),
}


def context_budget_for_model(model: str) -> ContextBudget:
    try:
        context_window, output_allowance = MODEL_CONTEXT_WINDOWS[model]
    except KeyError as exc:
        raise KeyError(model) from exc
    return ContextBudget.from_window(context_window, output_allowance)
