"""Embedding models package."""

from footballanalyst.embedding.base import EmbeddingModel
from footballanalyst.embedding.factory import EmbeddingModelFactory, get_embedding_model
from footballanalyst.embedding.gemini import GeminiEmbedding
from footballanalyst.embedding.sentence_transformer import SentenceTransformerEmbedding

__all__ = [
    "EmbeddingModel",
    "EmbeddingModelFactory",
    "GeminiEmbedding",
    "SentenceTransformerEmbedding",
    "get_embedding_model",
]
