from footballanalyst.ingestion.types import Chunk
from footballanalyst.retrieval.types import RetrievedContext
from footballanalyst.store.vector_store import ScoredChunk, VectorStore


class FakeLLMProvider:
    """Fake LLM provider for deterministic offline testing.

    ``complete()`` returns a fixed canned response that includes ``[1]`` so
    citation-parsing tests can assert non-empty citations without any network call.
    """

    CANNED_RESPONSE = (
        "Liverpool's high press was highly effective in the first half [1]. "
        "Klopp's 4-3-3 shape allowed the front three to trigger pressing traps [1]."
    )

    def complete(self, system: str, user: str) -> str:  # noqa: ARG002
        return self.CANNED_RESPONSE


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
        chunks = self.query_responses.get((collection, match_id), [])
        sorted_chunks = sorted(chunks, key=lambda sc: sc.score, reverse=True)
        return sorted_chunks[:top_k]


class FakeHybridRetriever:
    """Fake HybridRetriever for deterministic offline testing of ask().

    Pre-configure ``context`` to control the returned RetrievedContext.
    """

    def __init__(self, context: RetrievedContext | None = None) -> None:
        self.context = context if context is not None else RetrievedContext(chunks=[])
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, match_id: int) -> RetrievedContext:
        self.calls.append((query, match_id))
        return self.context
