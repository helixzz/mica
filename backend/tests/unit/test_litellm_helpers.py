from app.core.litellm_helpers import resolve_litellm_model


class TestOpenAICompatibleProviders:
    def test_raw_model_gets_openai_prefix(self):
        assert resolve_litellm_model("openai", "gpt-4o") == "openai/gpt-4o"

    def test_hf_style_slash_model_gets_openai_prefix(self):
        assert resolve_litellm_model("openai", "zai-org/glm-4.7") == "openai/zai-org/glm-4.7"

    def test_already_prefixed_is_unchanged(self):
        assert resolve_litellm_model("openai", "openai/gpt-4o") == "openai/gpt-4o"

    def test_deepseek_provider_routed_via_openai_compat(self):
        assert resolve_litellm_model("deepseek", "deepseek-chat") == "openai/deepseek-chat"

    def test_modelverse_alias_recognized(self):
        assert resolve_litellm_model("modelverse", "zai-org/glm-4.7") == "openai/zai-org/glm-4.7"

    def test_openai_compatible_alias_recognized(self):
        assert (
            resolve_litellm_model("openai-compatible", "claude-3-5-sonnet")
            == "openai/claude-3-5-sonnet"
        )

    def test_provider_casing_normalized(self):
        assert resolve_litellm_model("OpenAI", "gpt-4o") == "openai/gpt-4o"

    def test_provider_whitespace_trimmed(self):
        assert resolve_litellm_model("  openai  ", "gpt-4o") == "openai/gpt-4o"


class TestNativeLitellmProviders:
    def test_anthropic_model_passes_through(self):
        assert resolve_litellm_model("anthropic", "claude-3-5-sonnet") == "claude-3-5-sonnet"

    def test_bedrock_prefix_preserved(self):
        assert (
            resolve_litellm_model("bedrock", "bedrock/anthropic.claude-v2")
            == "bedrock/anthropic.claude-v2"
        )

    def test_mock_provider_unchanged(self):
        assert resolve_litellm_model("mock", "mock/demo") == "mock/demo"

    def test_dashscope_prefix_preserved(self):
        assert resolve_litellm_model("dashscope", "dashscope/qwen-turbo") == "dashscope/qwen-turbo"


class TestEdgeCases:
    def test_empty_model_returned_empty(self):
        assert resolve_litellm_model("openai", "") == ""

    def test_whitespace_only_model_returned_empty(self):
        assert resolve_litellm_model("openai", "   ") == ""

    def test_none_provider_falls_through(self):
        assert resolve_litellm_model(None, "gpt-4o") == "gpt-4o"

    def test_unknown_provider_falls_through(self):
        assert resolve_litellm_model("my-custom-llm", "some-model") == "some-model"

    def test_model_string_trimmed(self):
        assert resolve_litellm_model("openai", "  gpt-4o  ") == "openai/gpt-4o"
