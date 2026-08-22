import os

from footballanalyst.embedding.base import EmbeddingModel
from footballanalyst.embedding.gemini import GeminiEmbedding
from footballanalyst.embedding.sentence_transformer import SentenceTransformerEmbedding


class EmbeddingModelFactory:
    """Factory for creating EmbeddingModel instances."""

    @staticmethod
    def create(model_name: str | None = None) -> EmbeddingModel:
        """Create an EmbeddingModel instance based on model_name or env var."""
        selected = model_name or os.environ.get("EMBEDDING_MODEL", "local")
        if selected.lower() == "gemini":
            return GeminiEmbedding()
        return SentenceTransformerEmbedding()


def get_embedding_model(model_name: str | None = None) -> EmbeddingModel:
    """Convenience alias for EmbeddingModelFactory.create."""
    return EmbeddingModelFactory.create(model_name)
