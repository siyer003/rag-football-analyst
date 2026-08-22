from footballanalyst.ingestion.types import Chunk
from footballanalyst.store.vector_store import ScoredChunk, VectorStore


class FakeLLMProvider:
    """Fake LLM provider for deterministic offline testing."""

    pass


class FakeEmbeddingModel:
    """Fake embedding model for deterministic offline testing."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class FakeVectorStore(VectorStore):
    """Fake vector store for deterministic offline testing."""

    def __init__(self) -> None:
        self.upserted_chunks: list[tuple[list[Chunk], list[list[float]]]] = []
        self.query_responses: dict[tuple[str, int], list[ScoredChunk]] = {}
        self.chunks_by_id: dict[str, Chunk] = {}

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        self.upserted_chunks.append((chunks, embeddings))
        for chunk in chunks:
            self.chunks_by_id[chunk.chunk_id] = chunk

    def query(
        self,
        embedding: list[float],
        collection: str,
        match_id: int,
        top_k: int = 5,
    ) -> list[ScoredChunk]:
        return self.query_responses.get((collection, match_id), [])[:top_k]
