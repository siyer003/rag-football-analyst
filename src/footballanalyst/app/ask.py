from footballanalyst.app.types import Answer
from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.generation import LLMProvider
from footballanalyst.retrieval import HybridRetriever


def ask(
    query: str,
    match_id: int,
    retriever: HybridRetriever | None = None,
    llm: LLMProvider | None = None,
    registry: MatchRegistry | None = None,
) -> Answer:
    """Entrypoint to query tactical analysis for a match.

    Design rationale for parameters and defaults:
    - ``retriever`` & ``llm`` default to ``None`` to allow out-of-corpus guard checks
      and lightweight callers to execute without instantiating full ML pipelines.
    - ``registry`` defaults to ``None`` (loading from config/corpus.toml on demand),
      but accepts an injected ``MatchRegistry`` instance to prevent coupling callers or
      tests to global file system state.
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

    # Happy path will be implemented in ticket 09
    raise NotImplementedError("In-corpus query handling is not yet implemented.")
