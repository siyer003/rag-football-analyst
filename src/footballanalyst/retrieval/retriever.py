from typing import Protocol

from footballanalyst.retrieval.types import RetrievedContext


class HybridRetrieverProtocol(Protocol):
    """Protocol for hybrid retriever (ADR-0001). Seam used by ask()."""

    def retrieve(self, query: str, match_id: int) -> RetrievedContext:
        """Retrieve grounded context chunks for a given query and match_id."""
        ...
