import hashlib
import re

from footballanalyst.ingestion.types import NarrativeChunk, SourcePayload

TARGET_MIN_TOKENS = 150
TARGET_MAX_TOKENS = 250
HARD_CAP_TOKENS = 300
OVERLAP_PERCENT = 0.20


class NarrativeChunker:
    """Chunker that splits narrative texts into sliding-window NarrativeChunks."""

    def chunk(
        self, match_id: int, narratives: dict[str, SourcePayload]
    ) -> list[NarrativeChunk]:
        """Produce NarrativeChunks for given match_id and source narratives."""
        all_chunks: list[NarrativeChunk] = []
        used_ids: set[str] = set()

        for source, payload in narratives.items():
            url = payload.get("url", "")
            raw_text = payload.get("text", "").strip()
            if not raw_text:
                continue

            source_chunks = self._chunk_source_text(
                match_id=match_id,
                source=source,
                url=url,
                text=raw_text,
                used_ids=used_ids,
            )
            all_chunks.extend(source_chunks)

        return all_chunks

    def _chunk_source_text(
        self,
        match_id: int,
        source: str,
        url: str,
        text: str,
        used_ids: set[str],
    ) -> list[NarrativeChunk]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        units: list[str] = []

        for p in paragraphs:
            words = p.split()
            if len(words) > TARGET_MAX_TOKENS:
                # Split large paragraph into sentences
                sentences = re.split(r"(?<=[.!?]) +", p)
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    s_words = s_clean.split()
                    if len(s_words) > TARGET_MAX_TOKENS:
                        # Fallback word-chunking for giant sentences exceeding token cap
                        for i in range(0, len(s_words), TARGET_MAX_TOKENS):
                            block = " ".join(s_words[i : i + TARGET_MAX_TOKENS])
                            units.append(block)
                    else:
                        units.append(s_clean)
            else:
                units.append(p)

        chunks: list[NarrativeChunk] = []
        curr_units: list[str] = []
        curr_word_count = 0

        for unit in units:
            unit_words = unit.split()
            unit_len = len(unit_words)

            if curr_word_count + unit_len > TARGET_MAX_TOKENS and curr_units:
                # Emit current window
                chunk_text = "\n\n".join(curr_units)
                chunk_id = self._generate_chunk_id(
                    match_id=match_id,
                    source=source,
                    text=chunk_text,
                    used_ids=used_ids,
                )
                used_ids.add(chunk_id)
                chunks.append(
                    NarrativeChunk(
                        match_id=match_id,
                        source=source,
                        url=url,
                        text=chunk_text,
                        chunk_id=chunk_id,
                    )
                )

                # Calculate overlap (~20% of curr_word_count)
                overlap_target = int(curr_word_count * OVERLAP_PERCENT)
                new_units: list[str] = []
                accum_overlap = 0
                for unit_item in reversed(curr_units):
                    u_words = unit_item.split()
                    u_count = len(u_words)
                    needed = overlap_target - accum_overlap
                    if needed <= 0:
                        break
                    if u_count <= needed:
                        new_units.insert(0, unit_item)
                        accum_overlap += u_count
                    else:
                        overlap_words = u_words[-needed:]
                        new_units.insert(0, " ".join(overlap_words))
                        accum_overlap += len(overlap_words)
                        break

                curr_units = new_units
                curr_word_count = accum_overlap

            curr_units.append(unit)
            curr_word_count += unit_len

        if curr_units:
            chunk_text = "\n\n".join(curr_units)
            chunk_id = self._generate_chunk_id(
                match_id=match_id,
                source=source,
                text=chunk_text,
                used_ids=used_ids,
            )
            used_ids.add(chunk_id)
            chunks.append(
                NarrativeChunk(
                    match_id=match_id,
                    source=source,
                    url=url,
                    text=chunk_text,
                    chunk_id=chunk_id,
                )
            )

        return chunks

    def _generate_chunk_id(
        self, match_id: int, source: str, text: str, used_ids: set[str]
    ) -> str:
        snippet = text[:100]
        raw_key = f"{match_id}{source}{snippet}"
        chunk_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

        if chunk_id in used_ids:
            counter = 1
            while True:
                candidate_key = f"{match_id}{source}{counter}{snippet}"
                candidate_id = hashlib.sha256(
                    candidate_key.encode("utf-8")
                ).hexdigest()[:16]
                if candidate_id not in used_ids:
                    return candidate_id
                counter += 1

        return chunk_id
