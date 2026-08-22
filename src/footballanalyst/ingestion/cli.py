import argparse
import sys
from collections.abc import Sequence
from typing import cast

from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.embedding.factory import EmbeddingModelFactory
from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.narrative_chunker import NarrativeChunker
from footballanalyst.ingestion.narrative_fetcher import NarrativeFetcher
from footballanalyst.ingestion.pipeline import IngestionPipeline
from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.store.vector_store import VectorStore


def build_pipeline() -> IngestionPipeline:
    """Wire real production components into an IngestionPipeline instance."""
    registry = MatchRegistry.load()
    statsbomb_fetcher = StatsBombFetcher()
    event_chunker = EventSummaryChunker()
    narrative_fetcher = NarrativeFetcher()
    narrative_chunker = NarrativeChunker()
    embedding_model = EmbeddingModelFactory.create()
    vector_store = VectorStore()

    return IngestionPipeline(
        registry=registry,
        statsbomb_fetcher=statsbomb_fetcher,
        event_chunker=event_chunker,
        narrative_fetcher=narrative_fetcher,
        narrative_chunker=narrative_chunker,
        embedding_model=embedding_model,
        vector_store=vector_store,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for ingestion (`uv run ingest`)."""
    parser = argparse.ArgumentParser(
        description="Ingest StatsBomb events and narrative texts into vector store."
    )
    parser.add_argument(
        "--match-ids",
        nargs="+",
        type=int,
        help="Optional match IDs to ingest (e.g. --match-ids 3869685 3754058)",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    match_ids = cast(list[int] | None, args.match_ids)

    pipeline = build_pipeline()
    result = pipeline.run(match_ids=match_ids)

    if result.systemic_failures > 0:
        print(
            f"\n[CRITICAL ERROR] Systemic vector store / embedding failures "
            f"occurred on {result.systemic_failures} match(es)!"
        )

    if result.matches_failed > 0:
        print(
            f"\n[WARNING] Data fetch/chunking failed on "
            f"{result.matches_failed} match(es) (skipped)."
        )

    print("\n--- Ingestion Summary ---")
    print(f"Matches processed:   {result.matches_processed}")
    print(f"Fetch/chunk failed:  {result.matches_failed}")
    print(f"Systemic store fail: {result.systemic_failures}")
    print(f"Total chunks stored: {result.total_chunks_stored}")
    print(f"Elapsed time:        {result.elapsed_seconds:.2f}s\n")

    if result.systemic_failures > 0:
        return 2
    if result.matches_failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
