from typing import Protocol


class LLMProvider(Protocol):
    """Abstract protocol for LLM providers (ADR-0003)."""

    def complete(self, system: str, user: str) -> str:
        """Generate text completion for a given system prompt and user prompt."""
        ...
