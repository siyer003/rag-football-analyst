import os
from typing import Any


class GeminiEmbedding:
    """Embedding model using Google GenAI text-embedding-004."""

    def __init__(self, model_name: str = "text-embedding-004") -> None:
        self.model_name = model_name
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is not set")
            from google import genai

            self._client = genai.Client(api_key=api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        response = client.models.embed_content(
            model=self.model_name,
            contents=texts,
        )
        return [list(e.values) for e in response.embeddings]

    @property
    def dimension(self) -> int:
        return 768
