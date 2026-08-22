from footballanalyst.retrieval.base import _BaseVectorStoreRetriever


class EventRetriever(_BaseVectorStoreRetriever):
    """Retriever for structured event summary chunks."""

    @property
    def collection_name(self) -> str:
        return "event_summaries"
