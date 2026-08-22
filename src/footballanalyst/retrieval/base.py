from abc import ABC, abstractmethod

from footballanalyst.store.vector_store import ScoredChunk, VectorStore


class _BaseVectorStoreRetriever(ABC):
    """Abstract base retriever bound to a specific VectorStore collection."""

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Name of the collection to query."""
        ...

    def __init__(self, vector_store: VectorStore) -> None:
        self._vector_store = vector_store

    def retrieve(
        self,
        query_embedding: list[float],
        match_id: int,
        top_k: int = 5,
    ) -> list[ScoredChunk]:
        """Retrieve top_k ScoredChunk objects for the given match_id and query_embedding."""
        return self._vector_store.query(
            embedding=query_embedding,
            collection=self.collection_name,
            match_id=match_id,
            top_k=top_k,
        )
