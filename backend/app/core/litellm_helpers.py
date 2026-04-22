"""LiteLLM helpers: normalize model strings + provider overrides.

LiteLLM infers the provider from the ``model`` string's prefix. For OpenAI-compatible
endpoints (DeepSeek, GLM, Tongyi Qianwen via compatible API, Together AI, vLLM-hosted models,
etc.), the model string must be prefixed with ``openai/`` so LiteLLM knows to use its
generic OpenAI-compatible completion path with the user-supplied ``api_base`` and ``api_key``.

Without the prefix, model strings containing ``/`` (e.g. ``zai-org/glm-4.7``,
``deepseek-ai/DeepSeek-V3``) are misread as Hugging Face IDs and LiteLLM raises
``BadRequestError: LLM Provider NOT provided``.

This module centralizes that normalization so test-connection, streaming, and any future
call site behave consistently.
"""

from __future__ import annotations

# Providers that Mica treats as "OpenAI-compatible" — any model string under them
# is routed through LiteLLM's generic OpenAI path via api_base.
# The DB ``provider`` column is a free-form tag (user-chosen label); these values
# are the conventional ones we recognize for auto-prefixing.
OPENAI_COMPATIBLE_PROVIDERS: frozenset[str] = frozenset(
    {
        "openai",
        "openai-compatible",
        "openai_compatible",
        "deepseek",
        "modelverse",
        "glm",
        "zhipu",
        "tongyi-compatible",
        "doubao-compatible",
        "together",
        "vllm",
        "ollama-openai",
    }
)

# LiteLLM-native provider prefixes. If a model string already starts with any of these,
# we must NOT re-prefix; LiteLLM will route correctly on its own.
KNOWN_LITELLM_PREFIXES: tuple[str, ...] = (
    "openai/",
    "azure/",
    "anthropic/",
    "bedrock/",
    "vertex_ai/",
    "gemini/",
    "cohere/",
    "mistral/",
    "groq/",
    "deepseek/",
    "fireworks_ai/",
    "together_ai/",
    "perplexity/",
    "huggingface/",
    "replicate/",
    "ollama/",
    "xai/",
    "dashscope/",
    "volcengine/",
)


def resolve_litellm_model(provider: str | None, model_string: str) -> str:
    """Return a model string that LiteLLM can route without ambiguity.

    Rules:
    1. If ``model_string`` already starts with any known LiteLLM provider prefix,
       return it unchanged.
    2. If ``provider`` is in our OpenAI-compatible whitelist and the string has no
       recognized prefix, prepend ``openai/``.
    3. Otherwise return the original string (let LiteLLM decide / fail loudly).

    Examples:
        resolve_litellm_model("openai", "gpt-4o")                  -> "openai/gpt-4o"
        resolve_litellm_model("openai", "zai-org/glm-4.7")         -> "openai/zai-org/glm-4.7"
        resolve_litellm_model("openai", "openai/gpt-4o")           -> "openai/gpt-4o"
        resolve_litellm_model("deepseek", "deepseek-chat")         -> "openai/deepseek-chat"
        resolve_litellm_model("anthropic", "claude-3-5-sonnet")    -> "claude-3-5-sonnet"
        resolve_litellm_model("mock", "mock/demo")                 -> "mock/demo"
    """
    m = (model_string or "").strip()
    if not m:
        return m

    if m.startswith(KNOWN_LITELLM_PREFIXES):
        return m

    provider_normalized = (provider or "").strip().lower()
    if provider_normalized in OPENAI_COMPATIBLE_PROVIDERS:
        return f"openai/{m}"

    return m
