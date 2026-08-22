"""Factory for LLMProvider concrete implementations (ADR-0003)."""

import os

from footballanalyst.generation.provider import LLMProvider


class LLMProviderFactory:
    """Creates the appropriate LLMProvider based on the ``LLM_PROVIDER`` env var.

    Selection:
        - ``groq`` (default): returns ``GroqProvider``.
        - ``gemini``: returns ``GeminiProvider``.

    Raises ``ValueError`` for unknown provider names so misconfiguration surfaces
    immediately at startup rather than at query time.
    """

    @staticmethod
    def create() -> LLMProvider:
        """Instantiate and return the configured LLMProvider."""
        provider_name = os.environ.get("LLM_PROVIDER", "groq").lower()

        if provider_name == "groq":
            from footballanalyst.generation.groq_provider import GroqProvider

            return GroqProvider()

        if provider_name == "gemini":
            from footballanalyst.generation.gemini_provider import GeminiProvider

            return GeminiProvider()

        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider_name}'. "
            "Supported values: 'groq' (default), 'gemini'."
        )
