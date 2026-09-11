"""Well-known model providers and their allowed models for BYOK."""

from __future__ import annotations

from dataclasses import dataclass

MAX_MODELS_PER_PROVIDER = 5
CUSTOM_ENDPOINT_OPTION = "__custom_endpoint__"
CUSTOM_MODEL_OPTION = "__custom_model__"


@dataclass(frozen=True)
class ModelEntry:
    model_id: str
    label: str


@dataclass(frozen=True)
class ProviderEntry:
    provider_id: str
    label: str
    base_url: str
    models: tuple[ModelEntry, ...]


def _build_catalogue() -> tuple[ProviderEntry, ...]:
    providers = (
        ProviderEntry(
            provider_id="openai",
            label="OpenAI",
            base_url="https://api.openai.com",
            models=(
                ModelEntry("gpt-4o-mini", "GPT-4o mini"),
                ModelEntry("gpt-4.1-mini", "GPT-4.1 mini"),
                ModelEntry("gpt-4.1", "GPT-4.1"),
                ModelEntry("gpt-4.1-nano", "GPT-4.1 nano"),
                ModelEntry("o4-mini", "o4 mini"),
            ),
        ),
        ProviderEntry(
            provider_id="anthropic",
            label="Anthropic",
            base_url="https://api.anthropic.com",
            models=(
                ModelEntry("claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
                ModelEntry("claude-sonnet-4-20250514", "Claude Sonnet 4"),
                ModelEntry("claude-opus-4-20250514", "Claude Opus 4"),
                ModelEntry("claude-3-7-sonnet-latest", "Claude 3.7 Sonnet"),
                ModelEntry("claude-3-5-haiku-latest", "Claude 3.5 Haiku"),
            ),
        ),
        ProviderEntry(
            provider_id="moonshot",
            label="Moonshot (Kimi)",
            base_url="https://api.moonshot.cn/v1",
            models=(
                ModelEntry("moonshot-v1-8k", "Moonshot v1 8k"),
                ModelEntry("moonshot-v1-32k", "Moonshot v1 32k"),
                ModelEntry("moonshot-v1-128k", "Moonshot v1 128k"),
                ModelEntry("kimi-k2-0711-preview", "Kimi K2 preview"),
                ModelEntry("kimi-k2-turbo-preview", "Kimi K2 turbo preview"),
            ),
        ),
        ProviderEntry(
            provider_id="qwen",
            label="Qwen",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            models=(
                ModelEntry("qwen-plus", "Qwen Plus"),
                ModelEntry("qwen-turbo", "Qwen Turbo"),
                ModelEntry("qwen-max", "Qwen Max"),
                ModelEntry("qwen2.5-72b-instruct", "Qwen 2.5 72B"),
                ModelEntry("qwen2.5-32b-instruct", "Qwen 2.5 32B"),
            ),
        ),
        ProviderEntry(
            provider_id="openrouter",
            label="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            models=(
                ModelEntry("openai/gpt-4o-mini", "GPT-4o mini via OpenRouter"),
                ModelEntry("anthropic/claude-sonnet-4", "Claude Sonnet 4 via OpenRouter"),
                ModelEntry("google/gemini-2.5-pro", "Gemini 2.5 Pro via OpenRouter"),
                ModelEntry("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B via OpenRouter"),
                ModelEntry("deepseek/deepseek-chat", "DeepSeek Chat via OpenRouter"),
            ),
        ),
        ProviderEntry(
            provider_id="groq",
            label="Groq",
            base_url="https://api.groq.com/openai/v1",
            models=(
                ModelEntry("llama-3.3-70b-versatile", "Llama 3.3 70B"),
                ModelEntry("llama-3.1-8b-instant", "Llama 3.1 8B instant"),
                ModelEntry("mixtral-8x7b-32768", "Mixtral 8x7B"),
                ModelEntry("gemma2-9b-it", "Gemma 2 9B"),
                ModelEntry("llama-guard-3-8b", "Llama Guard 3 8B"),
            ),
        ),
        ProviderEntry(
            provider_id="xai",
            label="xAI (Grok)",
            base_url="https://api.x.ai/v1",
            models=(
                ModelEntry("grok-3", "Grok 3"),
                ModelEntry("grok-3-mini", "Grok 3 mini"),
                ModelEntry("grok-2-1212", "Grok 2"),
                ModelEntry("grok-2-vision-1212", "Grok 2 vision"),
                ModelEntry("grok-beta", "Grok beta"),
            ),
        ),
        ProviderEntry(
            provider_id="deepseek",
            label="DeepSeek",
            base_url="https://api.deepseek.com",
            models=(
                ModelEntry("deepseek-chat", "DeepSeek Chat"),
                ModelEntry("deepseek-reasoner", "DeepSeek Reasoner"),
                ModelEntry("deepseek-coder", "DeepSeek Coder"),
                ModelEntry("deepseek-v3", "DeepSeek V3"),
                ModelEntry("deepseek-r1", "DeepSeek R1"),
            ),
        ),
        ProviderEntry(
            provider_id="github-copilot",
            label="GitHub Copilot",
            base_url="https://api.githubcopilot.com",
            models=(
                ModelEntry("gpt-4.1", "GPT-4.1"),
                ModelEntry("gpt-4o", "GPT-4o"),
                ModelEntry("claude-sonnet-4", "Claude Sonnet 4"),
                ModelEntry("o4-mini", "o4 mini"),
                ModelEntry("o1", "o1"),
            ),
        ),
        ProviderEntry(
            provider_id="ollama",
            label="Ollama",
            base_url="http://127.0.0.1:11434/v1",
            models=(
                ModelEntry("llama3.3", "Llama 3.3"),
                ModelEntry("qwen2.5", "Qwen 2.5"),
                ModelEntry("mistral", "Mistral"),
                ModelEntry("codellama", "Code Llama"),
                ModelEntry("gemma2", "Gemma 2"),
            ),
        ),
        ProviderEntry(
            provider_id="opencode",
            label="OpenCode",
            base_url="http://127.0.0.1:4096/v1",
            models=(
                ModelEntry("opencode-default", "OpenCode default"),
                ModelEntry("opencode-fast", "OpenCode fast"),
                ModelEntry("opencode-balanced", "OpenCode balanced"),
                ModelEntry("opencode-quality", "OpenCode quality"),
                ModelEntry("opencode-coder", "OpenCode coder"),
            ),
        ),
    )
    for provider in providers:
        if len(provider.models) > MAX_MODELS_PER_PROVIDER:
            raise ValueError(
                f"{provider.provider_id} lists more than {MAX_MODELS_PER_PROVIDER} models"
            )
    return providers


CATALOGUE: tuple[ProviderEntry, ...] = _build_catalogue()


def list_providers() -> tuple[ProviderEntry, ...]:
    return CATALOGUE


def provider_for(provider_id: str) -> ProviderEntry:
    for provider in CATALOGUE:
        if provider.provider_id == provider_id:
            return provider
    raise KeyError(f"unknown provider: {provider_id}")


def base_url_for(provider_id: str) -> str:
    return provider_for(provider_id).base_url


def models_for(provider_id: str) -> tuple[ModelEntry, ...]:
    return provider_for(provider_id).models


def is_known_provider_model(provider_id: str, model_id: str) -> bool:
    try:
        return any(entry.model_id == model_id for entry in models_for(provider_id))
    except KeyError:
        return False


def default_model_for(provider_id: str) -> str:
    models = models_for(provider_id)
    return models[0].model_id
