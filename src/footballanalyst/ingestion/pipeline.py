import time
from collections.abc import Sequence
from dataclasses import dataclass

import structlog

from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.embedding.base import EmbeddingModel
from footballanalyst.ingestion.event_chunker import EventSummaryChunker
from footballanalyst.ingestion.narrative_chunker import NarrativeChunker
from footballanalyst.ingestion.narrative_fetcher import NarrativeFetcher
from footballanalyst.ingestion.statsbomb_fetcher import StatsBombFetcher
from footballanalyst.ingestion.types import Chunk
from footballanalyst.store.vector_store import VectorStore

logger = structlog.get_logger()


@dataclass
class IngestionResult:
    """Summary metrics of an ingestion run."""

    matches_processed: int
    matches_failed: int
    systemic_failures: int
    total_chunks_stored: int
    elapsed_seconds: float


class IngestionPipeline:
    """Pipeline orchestrating match fetching, chunking, and vector storage."""

    def __init__(
        self,
        registry: MatchRegistry,
        statsbomb_fetcher: StatsBombFetcher,
        event_chunker: EventSummaryChunker,
        narrative_fetcher: NarrativeFetcher,
        narrative_chunker: NarrativeChunker,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
    ) -> None:
        self.registry = registry
        self.statsbomb_fetcher = statsbomb_fetcher
        self.event_chunker = event_chunker
        self.narrative_fetcher = narrative_fetcher
        self.narrative_chunker = narrative_chunker
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def run(self, match_ids: Sequence[int] | None = None) -> IngestionResult:
        """Run ingestion pipeline over targeted match_ids or full registered corpus."""
        start_time = time.perf_counter()
        target_ids = list(
            match_ids if match_ids is not None else self.registry.match_ids()
        )

        processed_count = 0
        failed_count = 0
        systemic_failed_count = 0
        total_chunks = 0

        for match_id in target_ids:
            # 1. Fetch & Chunk Step (Per-match fault tolerant skip)
            try:
                match_config = self.registry.get_match(match_id)
                raw_events = self.statsbomb_fetcher.fetch(match_id)
                event_chunks = self.event_chunker.chunk(raw_events)

                home_team = str(raw_events.metadata.get("home_team", ""))
                away_team = str(raw_events.metadata.get("away_team", ""))
                teams = [t for t in [home_team, away_team] if t]

                narratives = self.narrative_fetcher.fetch(
                    match_id=match_id,
                    match_label=str(match_config.get("label", "")),
                    competition=str(match_config.get("competition", "")),
                    statsbomb_blog_url=str(match_config.get("statsbomb_blog_url", "")),
                    match_date=str(match_config.get("match_date", "")),
                    teams=teams,
                )
                narrative_chunks = self.narrative_chunker.chunk(match_id, narratives)
            except Exception as fetch_err:
                failed_count += 1
                logger.error(
                    "Match fetch or chunking failed",
                    match_id=match_id,
                    error=str(fetch_err),
                    step="fetch_chunk",
                    exc_info=True,
                )
                continue

            all_chunks: list[Chunk] = [*event_chunks, *narrative_chunks]
            if not all_chunks:
                processed_count += 1
                logger.info(
                    "Match produced zero chunks",
                    match_id=match_id,
                    chunk_count=0,
                    step="ingest",
                )
                continue

            # 2. Embed & Upsert Step (Systemic store failures)
            try:
                t_embed_start = time.perf_counter()
                texts = [c.text for c in all_chunks]
                embeddings = self.embedding_model.embed(texts)
                embed_time_ms = (time.perf_counter() - t_embed_start) * 1000.0

                self.vector_store.upsert(all_chunks, embeddings)
                chunk_count = len(all_chunks)
                total_chunks += chunk_count
                processed_count += 1

                logger.info(
                    "Match ingestion complete",
                    match_id=match_id,
                    chunk_count=chunk_count,
                    embed_time_ms=round(embed_time_ms, 2),
                    upsert_count=chunk_count,
                    step="upsert",
                )
            except Exception as store_err:
                systemic_failed_count += 1
                logger.error(
                    "Systemic embedding or vector store failure",
                    match_id=match_id,
                    error=str(store_err),
                    step="embed_upsert",
                    exc_info=True,
                )

        elapsed = time.perf_counter() - start_time
        return IngestionResult(
            matches_processed=processed_count,
            matches_failed=failed_count,
            systemic_failures=systemic_failed_count,
            total_chunks_stored=total_chunks,
            elapsed_seconds=elapsed,
        )
