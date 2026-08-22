from footballanalyst.retrieval.base import _BaseVectorStoreRetriever


class NarrativeRetriever(_BaseVectorStoreRetriever):
    """Retriever for unstructured narrative chunks."""

    @property
    def collection_name(self) -> str:
        return "narrative_chunks"
