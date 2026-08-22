from typing import Protocol


class EmbeddingModel(Protocol):
    """Abstract protocol for text embedding models."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings into vector representations."""
        ...

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality of the embedding model."""
        ...
