"""Citation extraction from LLM answer text."""

import re

import structlog

from footballanalyst.app.types import ChunkRef
from footballanalyst.retrieval.types import RetrievedContext

log = structlog.get_logger(__name__)

_CITATION_RE = re.compile(r"\[(\d+)\]")


def parse_citations(answer_text: str, context: RetrievedContext) -> list[ChunkRef]:
    """Extract [N] citation references from LLM answer text and map to ChunkRef objects.

    Indexes are 1-based, matching the numbering used by build_prompt().
    Duplicate citations are deduplicated; order is preserved by first occurrence.
    Out-of-range indexes are silently dropped from the returned list, but a
    structlog WARNING is emitted for each so that the eval harness (Ticket 11)
    can surface grounding quality issues without exposing them to the end user.

    Args:
        answer_text: The raw text returned by the LLMProvider.
        context: The RetrievedContext used to build the prompt.

    Returns:
        A deduplicated list of ChunkRef objects in first-occurrence order.
    """
    max_index = len(context.chunks)
    seen: set[int] = set()
    refs: list[ChunkRef] = []

    for m in _CITATION_RE.finditer(answer_text):
        idx = int(m.group(1))  # 1-based
        if idx in seen:
            continue
        seen.add(idx)

        if idx < 1 or idx > max_index:
            log.warning(
                "parse_citations.out_of_range",
                cited_index=idx,
                max_valid_index=max_index,
            )
            continue

        ranked = context.chunks[idx - 1]
        chunk = ranked.chunk
        refs.append(
            ChunkRef(
                chunk_id=chunk.chunk_id,
                source=chunk.source,
                chunk_type=chunk.chunk_type,
                snippet=chunk.text,
            )
        )

    return refs
