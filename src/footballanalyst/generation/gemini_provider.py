"""Gemini LLM provider (ADR-0003)."""

import os


class GeminiProvider:
    """LLM provider backed by Google's Gemini API using gemini-2.0-flash.

    Requires the ``GOOGLE_API_KEY`` environment variable to be set.
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self) -> None:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        from google import genai  # local import — SDK not needed until instantiation

        self._client = genai.Client(api_key=api_key)

    def complete(self, system: str, user: str) -> str:
        """Call Gemini generate_content and return the response text."""
        combined_prompt = f"{system}\n\n{user}"
        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=combined_prompt,
        )
        return response.text or ""
