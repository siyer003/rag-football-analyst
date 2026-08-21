from dataclasses import dataclass, field


@dataclass
class ChunkRef:
    """Reference to a grounding chunk used in an Answer citation."""

    chunk_id: str
    source: str
    chunk_type: str
    snippet: str


@dataclass
class Answer:
    """LLM-generated answer grounded in retrieved context."""

    text: str
    citations: list[ChunkRef] = field(default_factory=list)
    out_of_corpus: bool = False
