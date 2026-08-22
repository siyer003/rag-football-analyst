from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import chromadb

from footballanalyst.ingestion.types import Chunk, EventSummary, NarrativeChunk


@dataclass
class ScoredChunk:
    """Retrieved chunk bundled with its similarity/distance score."""

    chunk: Chunk
    score: float


class VectorStore:
    """ChromaDB persistence store for EventSummary and NarrativeChunk vectors."""

    def __init__(self, persist_directory: str | Path | None = None) -> None:
        if persist_directory is None:
            persist_directory = Path("data/chroma")
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_directory))

    def _get_collection_name(self, chunk: Chunk) -> str:
        if chunk.chunk_type == "event_summary" or isinstance(chunk, EventSummary):
            return "event_summaries"
        return "narrative_chunks"

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks and embeddings into the corresponding ChromaDB collections."""
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        grouped: dict[str, dict[str, list[Any]]] = {
            "event_summaries": {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "embeddings": [],
            },
            "narrative_chunks": {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "embeddings": [],
            },
        }

        for chunk, emb in zip(chunks, embeddings, strict=True):
            col_name = self._get_collection_name(chunk)
            metadata: dict[str, Any] = {
                "match_id": chunk.match_id,
                "chunk_type": chunk.chunk_type,
                "source": chunk.source,
            }
            if isinstance(chunk, EventSummary):
                metadata["window"] = chunk.window
            elif isinstance(chunk, NarrativeChunk):
                metadata["url"] = chunk.url

            grouped[col_name]["ids"].append(chunk.chunk_id)
            grouped[col_name]["documents"].append(chunk.text)
            grouped[col_name]["metadatas"].append(metadata)
            grouped[col_name]["embeddings"].append(emb)

        for col_name, data in grouped.items():
            if data["ids"]:
                collection = self._client.get_or_create_collection(
                    name=col_name,
                    metadata={"hnsw:space": "cosine"},
                )
                collection.upsert(
                    ids=data["ids"],
                    documents=data["documents"],
                    metadatas=data["metadatas"],
                    embeddings=data["embeddings"],
                )

    def query(
        self,
        embedding: list[float],
        collection: str,
        match_id: int,
        top_k: int = 5,
    ) -> list[ScoredChunk]:
        """Query ChromaDB collection filtered by match_id for top_k similar chunks."""
        col = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )
        results = col.query(
            query_embeddings=cast(Any, [embedding]),
            n_results=top_k,
            where={"match_id": match_id},
        )

        scored_chunks: list[ScoredChunk] = []

        ids_list = results.get("ids", [])
        if not ids_list or not ids_list[0]:
            return scored_chunks

        ids = ids_list[0]
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        for i, chunk_id in enumerate(ids):
            doc_text = str(documents[i]) if i < len(documents) else ""
            meta = dict(metadatas[i]) if i < len(metadatas) and metadatas[i] else {}
            has_dist = i < len(distances) and distances[i] is not None
            dist = float(distances[i]) if has_dist else 0.0
            similarity_score = max(0.0, 1.0 - dist)

            chunk_type = str(meta.get("chunk_type", ""))

            raw_match_id = meta.get("match_id", match_id)
            c_match_id = (
                int(raw_match_id)
                if isinstance(raw_match_id, (int, str, float))
                else match_id
            )
            c_source = str(meta.get("source", ""))

            reconstructed_chunk: Chunk
            if chunk_type == "event_summary" or collection == "event_summaries":
                reconstructed_chunk = EventSummary(
                    match_id=c_match_id,
                    window=str(meta.get("window", "")),
                    text=doc_text,
                    chunk_id=chunk_id,
                    chunk_type=chunk_type or "event_summary",
                    source=c_source or "statsbomb",
                )
            else:
                reconstructed_chunk = NarrativeChunk(
                    match_id=c_match_id,
                    source=c_source,
                    url=str(meta.get("url", "")),
                    text=doc_text,
                    chunk_id=chunk_id,
                    chunk_type=chunk_type or "narrative",
                )

            scored_chunks.append(
                ScoredChunk(chunk=reconstructed_chunk, score=similarity_score)
            )

        return scored_chunks

