"""Groq LLM provider (ADR-0003)."""

import os


class LLMConfigError(Exception):
    """Raised when a required LLM provider configuration is missing or invalid."""


class GroqProvider:
    """LLM provider backed by Groq's API using llama-3.3-70b-versatile.

    Requires the ``GROQ_API_KEY`` environment variable to be set.
    Raises ``LLMConfigError`` on construction if the key is absent, so callers
    receive a clear domain error rather than a raw SDK exception.
    """

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "GROQ_API_KEY environment variable is not set. "
                "Obtain a key from https://console.groq.com and export it."
            )
        from groq import Groq  # local import — SDK not needed until instantiation

        self._client = Groq(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        """Call Groq chat completion and return the assistant message text."""
        response = self._client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        return content if content is not None else ""
