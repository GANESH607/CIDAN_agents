import pytest

from cidan.config import get_settings


def test_llm_max_output_tokens_defaults_to_reduced_limit(monkeypatch):
    monkeypatch.delenv("LLM_MAX_OUTPUT_TOKENS", raising=False)

    assert get_settings().llm_max_output_tokens == 400


def test_llm_max_output_tokens_can_be_configured(monkeypatch):
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "300")

    assert get_settings().llm_max_output_tokens == 300


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_llm_max_output_tokens_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", value)

    with pytest.raises(ValueError, match="positive integer"):
        get_settings()


def test_sandbox_output_tokens_use_separate_validated_budget(monkeypatch):
    monkeypatch.delenv("SANDBOX_LLM_MAX_OUTPUT_TOKENS", raising=False)
    assert get_settings().sandbox_llm_max_output_tokens == 1200
    monkeypatch.setenv("SANDBOX_LLM_MAX_OUTPUT_TOKENS", "1800")
    assert get_settings().sandbox_llm_max_output_tokens == 1800
    monkeypatch.setenv("SANDBOX_LLM_MAX_OUTPUT_TOKENS", "0")
    with pytest.raises(ValueError, match="positive integer"):
        get_settings()
