"""Tests for provider selection, credentials validation, and timeout budget calculations."""

import pytest

from app.services.providers.config import read_provider_config


def test_gemini_primary_groq_fallback_config():
    environ = {
        "AI_PRIMARY_PROVIDER": "gemini",
        "AI_FALLBACK_PROVIDER": "groq",
        "GEMINI_GENERATION_TIMEOUT_MS": "28000",
        "GROQ_TIMEOUT_MS": "15000",
        "RAG_TIMEOUT_MS": "9000",
        "AI_TOTAL_TIMEOUT_MS": "55000",
    }
    cfg = read_provider_config(environ)
    assert cfg.primary_provider == "gemini"
    assert cfg.fallback_provider == "groq"
    assert cfg.primary_timeout_ms == 28000
    assert cfg.fallback_timeout_ms == 15000
    assert cfg.rag_timeout_ms == 9000
    assert cfg.total_planned_timeout_ms == 52000
    assert cfg.total_planned_timeout_ms <= cfg.ai_total_timeout_ms


def test_groq_primary_gemini_fallback_config():
    environ = {
        "AI_PRIMARY_PROVIDER": "groq",
        "AI_FALLBACK_PROVIDER": "gemini",
        "GEMINI_GENERATION_TIMEOUT_MS": "28000",
        "GROQ_TIMEOUT_MS": "15000",
        "RAG_TIMEOUT_MS": "9000",
        "AI_TOTAL_TIMEOUT_MS": "55000",
    }
    cfg = read_provider_config(environ)
    assert cfg.primary_provider == "groq"
    assert cfg.fallback_provider == "gemini"
    assert cfg.primary_timeout_ms == 15000
    assert cfg.fallback_timeout_ms == 28000
    assert cfg.total_planned_timeout_ms == 52000


def test_gemini_without_fallback():
    environ = {
        "AI_PRIMARY_PROVIDER": "gemini",
        "AI_FALLBACK_PROVIDER": "none",
        "GEMINI_GENERATION_TIMEOUT_MS": "38000",
        "RAG_TIMEOUT_MS": "9000",
    }
    cfg = read_provider_config(environ)
    assert cfg.primary_provider == "gemini"
    assert cfg.fallback_provider is None
    assert cfg.primary_timeout_ms == 38000
    assert cfg.fallback_timeout_ms == 0
    assert cfg.total_planned_timeout_ms == 47000


def test_groq_without_fallback():
    environ = {
        "AI_PRIMARY_PROVIDER": "groq",
        "AI_FALLBACK_PROVIDER": "",
        "GROQ_TIMEOUT_MS": "15000",
        "RAG_TIMEOUT_MS": "9000",
    }
    cfg = read_provider_config(environ)
    assert cfg.primary_provider == "groq"
    assert cfg.fallback_provider is None
    assert cfg.primary_timeout_ms == 15000
    assert cfg.fallback_timeout_ms == 0
    assert cfg.total_planned_timeout_ms == 24000


def test_provider_names_normalize_case_and_whitespace():
    environ = {
        "AI_PRIMARY_PROVIDER": "  GEMINI  ",
        "AI_FALLBACK_PROVIDER": "  GrOq  ",
    }
    cfg = read_provider_config(environ)
    assert cfg.primary_provider == "gemini"
    assert cfg.fallback_provider == "groq"


def test_unknown_primary_provider_fails():
    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "openai"})
    assert "Unknown AI_PRIMARY_PROVIDER: 'openai'" in str(exc.value)


def test_empty_primary_provider_fails():
    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "none"})
    assert "cannot be empty or 'none'" in str(exc.value)


def test_unknown_fallback_provider_fails():
    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "gemini", "AI_FALLBACK_PROVIDER": "anthropic"})
    assert "Unknown AI_FALLBACK_PROVIDER: 'anthropic'" in str(exc.value)


@pytest.mark.parametrize("none_val", ["none", "NONE", "  none  ", "", "null", "false"])
def test_none_fallback_normalizes_to_disabled(none_val):
    cfg = read_provider_config({"AI_PRIMARY_PROVIDER": "gemini", "AI_FALLBACK_PROVIDER": none_val})
    assert cfg.fallback_provider is None


def test_identical_primary_and_fallback_fails():
    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "gemini", "AI_FALLBACK_PROVIDER": "gemini"})
    assert "cannot be identical" in str(exc.value)

    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "groq", "AI_FALLBACK_PROVIDER": "groq"})
    assert "cannot be identical" in str(exc.value)


def test_missing_required_primary_credentials():
    # Gemini as primary without key
    with pytest.raises(ValueError) as exc:
        read_provider_config(
            {"AI_PRIMARY_PROVIDER": "gemini", "AI_FALLBACK_PROVIDER": "none", "GEMINI_MODEL": "m"},
            check_credentials=True,
        )
    assert "GEMINI_API_KEY is required" in str(exc.value)

    # Groq as primary without key
    with pytest.raises(ValueError) as exc:
        read_provider_config(
            {"AI_PRIMARY_PROVIDER": "groq", "AI_FALLBACK_PROVIDER": "none", "GROQ_MODEL": "m"},
            check_credentials=True,
        )
    assert "GROQ_API_KEY is required" in str(exc.value)


def test_missing_required_fallback_credentials():
    # Groq as fallback without key
    with pytest.raises(ValueError) as exc:
        read_provider_config(
            {
                "AI_PRIMARY_PROVIDER": "gemini",
                "GEMINI_API_KEY": "valid_key",
                "GEMINI_MODEL": "gemini-3.5-flash",
                "AI_FALLBACK_PROVIDER": "groq",
                "GROQ_MODEL": "openai/gpt-oss-120b",
            },
            check_credentials=True,
        )
    assert "GROQ_API_KEY is required" in str(exc.value)


def test_disabled_fallback_does_not_require_credentials():
    # Fallback disabled -> missing GROQ_API_KEY is completely fine
    cfg = read_provider_config(
        {
            "AI_PRIMARY_PROVIDER": "gemini",
            "GEMINI_API_KEY": "valid_key",
            "GEMINI_MODEL": "gemini-3.5-flash",
            "AI_FALLBACK_PROVIDER": "none",
        },
        check_credentials=True,
    )
    assert cfg.primary_provider == "gemini"
    assert cfg.fallback_provider is None


@pytest.mark.parametrize(
    "bad_timeout",
    [
        {"RAG_TIMEOUT_MS": "0"},
        {"RAG_TIMEOUT_MS": "-1"},
        {"RAG_TIMEOUT_MS": "abc"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "0"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "-500"},
        {"GEMINI_GENERATION_TIMEOUT_MS": "3.5"},
        {"GROQ_TIMEOUT_MS": "-15000"},
        {"AI_TOTAL_TIMEOUT_MS": "0"},
    ],
)
def test_invalid_timeout_values_fail(bad_timeout):
    with pytest.raises(ValueError) as exc:
        read_provider_config({"AI_PRIMARY_PROVIDER": "gemini", **bad_timeout})
    assert "positive integer" in str(exc.value).lower() or "must be an integer" in str(exc.value).lower()


def test_combined_timeout_budget_violation_fails():
    # 38000 + 9000 + 15000 = 62000 > 55000
    with pytest.raises(ValueError) as exc:
        read_provider_config(
            {
                "AI_PRIMARY_PROVIDER": "gemini",
                "AI_FALLBACK_PROVIDER": "groq",
                "GEMINI_GENERATION_TIMEOUT_MS": "38000",
                "RAG_TIMEOUT_MS": "9000",
                "GROQ_TIMEOUT_MS": "15000",
                "AI_TOTAL_TIMEOUT_MS": "55000",
            }
        )
    msg = str(exc.value)
    assert "Combined AI timeout budget (62000 ms" in msg
    assert "exceeds AI_TOTAL_TIMEOUT_MS (55000 ms)" in msg


def test_no_secret_value_appears_in_errors():
    secret_key = "sk-super-secret-key-123456"
    with pytest.raises(ValueError) as exc:
        read_provider_config(
            {
                "AI_PRIMARY_PROVIDER": "invalid_provider",
                "GEMINI_API_KEY": secret_key,
                "GROQ_API_KEY": secret_key,
            }
        )
    assert secret_key not in str(exc.value)


def test_default_groq_model_is_openai_gpt_oss_120b():
    cfg = read_provider_config({})
    assert cfg.groq_model == "openai/gpt-oss-120b"


def test_deprecated_llama_model_absent_from_defaults():
    import app.config as app_config
    cfg = read_provider_config({})
    assert cfg.groq_model != "llama-3.3-70b-versatile"
    assert app_config.GROQ_MODEL != "llama-3.3-70b-versatile"
    assert "llama-3.3-70b-versatile" not in cfg.groq_model
