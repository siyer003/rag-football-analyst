"""Application entrypoint: ask() — the single public seam for query answering."""

from footballanalyst.app.types import Answer
from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.generation import LLMProvider
from footballanalyst.generation.citations import parse_citations
from footballanalyst.generation.prompt import build_prompt
from footballanalyst.retrieval import HybridRetrieverProtocol


def ask(
    query: str,
    match_id: int,
    retriever: HybridRetrieverProtocol | None = None,
    llm: LLMProvider | None = None,
    registry: MatchRegistry | None = None,
) -> Answer:
    """Entrypoint to query tactical analysis for a match.

    Full flow for in-corpus matches:
        1. Out-of-corpus guard — returns early with ``Answer(out_of_corpus=True)``
           if ``match_id`` is not in the registry.
        2. Retrieval — calls ``retriever.retrieve(query, match_id)`` to obtain a
           ``RetrievedContext`` from the HybridRetriever.
        3. Prompt assembly — ``build_prompt()`` converts the context into a
           (system, user) tuple.
        4. LLM completion — ``llm.complete(system, user)`` returns the answer text.
        5. Citation parsing — ``parse_citations()`` extracts ``[N]`` references and
           maps them to ``ChunkRef`` objects. Out-of-range references are dropped
           with a structlog WARNING (see ``citations.py``).

    Error handling:
        - LLM call failures (timeout, rate limit, API error) propagate as-is.
          No catch/retry logic is applied in v1. See ``docs/deferred.md``.

    Design rationale for parameters and defaults:
        - ``retriever`` & ``llm`` default to ``None`` to allow out-of-corpus guard
          checks and lightweight callers to execute without instantiating full ML
          pipelines.
        - ``registry`` defaults to ``None`` (loading from config/corpus.toml on
          demand), but accepts an injected ``MatchRegistry`` instance to prevent
          coupling callers or tests to global file system state.
    """
    if registry is None:
        registry = MatchRegistry.load()

    if match_id not in registry:
        available_matches = "\n".join(
            f"- [{mid}] {registry.label(mid)}" for mid in registry.match_ids()
        )
        message = (
            f"Match ID {match_id} is not in corpus. "
            f"Available matches are:\n{available_matches}"
        )
        return Answer(
            text=message,
            citations=[],
            out_of_corpus=True,
        )

    # Happy path: retrieve → prompt → LLM → citations
    assert retriever is not None, (
        "retriever must be provided for in-corpus match IDs"
    )
    assert llm is not None, (
        "llm must be provided for in-corpus match IDs"
    )

    context = retriever.retrieve(query, match_id)
    system_prompt, user_prompt = build_prompt(query, context)
    answer_text = llm.complete(system_prompt, user_prompt)
    citations = parse_citations(answer_text, context)

    return Answer(
        text=answer_text,
        citations=citations,
        out_of_corpus=False,
    )
