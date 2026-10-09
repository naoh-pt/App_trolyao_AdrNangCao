"""Configuration parsing and validation for generation providers."""

from dataclasses import dataclass
from typing import Mapping

ALLOWED_PROVIDERS = {"gemini", "groq"}


@dataclass(frozen=True)
class ProviderConfig:
    """Validated provider configuration settings."""

    primary_provider: str
    fallback_provider: str | None
    gemini_api_key: str | None
    gemini_model: str
    groq_api_key: str | None
    groq_model: str | None
    rag_timeout_ms: int
    gemini_generation_timeout_ms: int
    groq_timeout_ms: int
    ai_total_timeout_ms: int

    @property
    def primary_timeout_ms(self) -> int:
        return (
            self.gemini_generation_timeout_ms
            if self.primary_provider == "gemini"
            else self.groq_timeout_ms
        )

    @property
    def fallback_timeout_ms(self) -> int:
        if not self.fallback_provider:
            return 0
        return (
            self.gemini_generation_timeout_ms
            if self.fallback_provider == "gemini"
            else self.groq_timeout_ms
        )

    @property
    def total_planned_timeout_ms(self) -> int:
        return self.rag_timeout_ms + self.primary_timeout_ms + self.fallback_timeout_ms


def read_provider_config(
    environ: Mapping[str, str], check_credentials: bool = False
) -> ProviderConfig:
    """Parse and validate provider and timeout configuration.

    Args:
        environ: Mapping of environment variables.
        check_credentials: If True, validates presence of API keys and models for enabled providers.

    Raises:
        ValueError: If provider names, timeouts, credentials, or combined budget are invalid.
    """
    # 1. Parse primary provider
    primary_raw = environ.get("AI_PRIMARY_PROVIDER", "gemini")
    if primary_raw is None:
        raise ValueError("AI_PRIMARY_PROVIDER cannot be empty or 'none'")
    primary = primary_raw.strip().lower()
    if not primary or primary == "none":
        raise ValueError("AI_PRIMARY_PROVIDER cannot be empty or 'none'")
    if primary not in ALLOWED_PROVIDERS:
        raise ValueError(
            f"Unknown AI_PRIMARY_PROVIDER: '{primary}'. Allowed providers: {', '.join(sorted(ALLOWED_PROVIDERS))}"
        )

    # 2. Parse fallback provider
    fallback_raw = environ.get("AI_FALLBACK_PROVIDER", "groq")
    if fallback_raw is None:
        fallback = None
    else:
        fallback_clean = fallback_raw.strip().lower()
        if fallback_clean in {"none", "", "null", "false"}:
            fallback = None
        elif fallback_clean not in ALLOWED_PROVIDERS:
            raise ValueError(
                f"Unknown AI_FALLBACK_PROVIDER: '{fallback_clean}'. Allowed providers: {', '.join(sorted(ALLOWED_PROVIDERS))}, none"
            )
        else:
            fallback = fallback_clean

    # 3. Disallow identical primary and fallback
    if fallback is not None and primary == fallback:
        raise ValueError(f"AI_PRIMARY_PROVIDER and AI_FALLBACK_PROVIDER cannot be identical ('{primary}')")

    # 4. Parse timeouts
    def parse_int(key: str, default: int) -> int:
        raw = environ.get(key)
        if raw is None:
            return default
        try:
            val = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Timeout {key} must be an integer, got: '{raw}'") from exc
        if val <= 0:
            raise ValueError(f"Timeout {key} must be a positive integer, got: {val}")
        return val

    # Default generation timeout: 28000 when fallback is enabled, 38000 without fallback
    default_gen_timeout = 28000 if fallback else 38000
    gen_raw = environ.get("GEMINI_GENERATION_TIMEOUT_MS")
    if gen_raw is None:
        gen_raw = environ.get("GEMINI_TIMEOUT_MS")
    if gen_raw is not None:
        try:
            gemini_gen_timeout = int(gen_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Timeout GEMINI_GENERATION_TIMEOUT_MS must be an integer, got: '{gen_raw}'") from exc
        if gemini_gen_timeout <= 0:
            raise ValueError(f"Timeout GEMINI_GENERATION_TIMEOUT_MS must be a positive integer, got: {gemini_gen_timeout}")
    else:
        gemini_gen_timeout = default_gen_timeout

    rag_timeout = parse_int("RAG_TIMEOUT_MS", 9000)
    groq_timeout = parse_int("GROQ_TIMEOUT_MS", 15000)
    total_budget = parse_int("AI_TOTAL_TIMEOUT_MS", 55000)

    # 5. Combined timeout budget validation
    primary_timeout = gemini_gen_timeout if primary == "gemini" else groq_timeout
    fallback_timeout = (
        (gemini_gen_timeout if fallback == "gemini" else groq_timeout) if fallback else 0
    )
    total_planned = rag_timeout + primary_timeout + fallback_timeout

    if total_planned > total_budget:
        raise ValueError(
            f"Combined AI timeout budget ({total_planned} ms = RAG {rag_timeout}ms + "
            f"Primary {primary_timeout}ms + Fallback {fallback_timeout}ms) exceeds "
            f"AI_TOTAL_TIMEOUT_MS ({total_budget} ms)"
        )

    # 6. Models and keys
    gemini_key = environ.get("GEMINI_API_KEY")
    gemini_model = environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    groq_key = environ.get("GROQ_API_KEY")
    groq_model = environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    # 7. Credential checks (when required)
    if check_credentials:
        enabled_providers = {primary}
        if fallback:
            enabled_providers.add(fallback)

        if "gemini" in enabled_providers:
            if not gemini_key or not gemini_key.strip():
                role = "primary" if primary == "gemini" else "fallback"
                raise ValueError(f"GEMINI_API_KEY is required when Gemini is {role} provider")
            if not gemini_model or not gemini_model.strip():
                role = "primary" if primary == "gemini" else "fallback"
                raise ValueError(f"GEMINI_MODEL is required when Gemini is {role} provider")

        if "groq" in enabled_providers:
            if not groq_key or not groq_key.strip():
                role = "primary" if primary == "groq" else "fallback"
                raise ValueError(f"GROQ_API_KEY is required when Groq is {role} provider")
            if not groq_model or not groq_model.strip():
                role = "primary" if primary == "groq" else "fallback"
                raise ValueError(f"GROQ_MODEL is required when Groq is {role} provider")

    return ProviderConfig(
        primary_provider=primary,
        fallback_provider=fallback,
        gemini_api_key=gemini_key.strip() if gemini_key else None,
        gemini_model=gemini_model.strip() if gemini_model else "gemini-3.5-flash",
        groq_api_key=groq_key.strip() if groq_key else None,
        groq_model=groq_model.strip() if groq_model else None,
        rag_timeout_ms=rag_timeout,
        gemini_generation_timeout_ms=gemini_gen_timeout,
        groq_timeout_ms=groq_timeout,
        ai_total_timeout_ms=total_budget,
    )
