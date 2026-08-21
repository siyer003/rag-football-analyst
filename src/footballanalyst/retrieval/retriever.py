from typing import Any, Protocol


class HybridRetriever(Protocol):
    """Abstract protocol for hybrid retriever (ADR-0001)."""

    def retrieve(self, query: str, match_id: int) -> Any:
        """Retrieve grounded context chunks for a given query and match_id."""
        ...
