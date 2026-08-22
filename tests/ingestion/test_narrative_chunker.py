import json
from pathlib import Path

from footballanalyst.ingestion.narrative_chunker import NarrativeChunker
from footballanalyst.ingestion.types import NarrativeChunk, SourcePayload

FIXTURE_DIR = Path("tests/fixtures/narrative")


def load_fixture_payloads() -> dict[str, SourcePayload]:
    payloads: dict[str, SourcePayload] = {}
    sources = ["guardian", "wikipedia", "statsbomb_blog"]
    for source in sources:
        txt_path = FIXTURE_DIR / f"{source}_3869685.txt"
        json_path = FIXTURE_DIR / f"{source}_3869685.json"
        text = txt_path.read_text(encoding="utf-8").strip()
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        payloads[source] = {"url": str(meta["url"]), "text": text}
    return payloads


def test_chunker_produces_chunks_from_fixture_text() -> None:
    payloads = load_fixture_payloads()
    chunker = NarrativeChunker()
    chunks = chunker.chunk(match_id=3869685, narratives=payloads)

    assert len(chunks) >= 3
    sources = {c.source for c in chunks}
    assert {"guardian", "wikipedia", "statsbomb_blog"}.issubset(sources)


def test_chunk_has_required_fields_and_valid_token_count() -> None:
    payloads = load_fixture_payloads()
    chunker = NarrativeChunker()
    chunks = chunker.chunk(match_id=3869685, narratives=payloads)

    for c in chunks:
        assert isinstance(c, NarrativeChunk)
        assert c.match_id == 3869685
        assert c.chunk_type == "narrative"
        assert c.source in {"guardian", "wikipedia", "statsbomb_blog"}
        assert len(c.url) > 0
        assert len(c.text) > 0
        assert len(c.chunk_id) > 0
        # Token count (word count proxy) must be <= 300 per acceptance criteria
        words = c.text.split()
        assert len(words) <= 300


def test_chunk_ids_are_deterministic() -> None:
    payloads = load_fixture_payloads()
    chunker = NarrativeChunker()

    chunks1 = chunker.chunk(match_id=3869685, narratives=payloads)
    chunks2 = chunker.chunk(match_id=3869685, narratives=payloads)

    ids1 = [c.chunk_id for c in chunks1]
    ids2 = [c.chunk_id for c in chunks2]

    assert ids1 == ids2


def test_all_chunk_ids_are_unique_across_full_match() -> None:
    payloads = load_fixture_payloads()
    chunker = NarrativeChunker()

    chunks = chunker.chunk(match_id=3869685, narratives=payloads)
    chunk_ids = [c.chunk_id for c in chunks]

    assert len(chunk_ids) == len(set(chunk_ids))


def test_giant_sentence_split_fallback_enforces_token_cap() -> None:
    # A single sentence with 500 words and no period punctuation inside
    giant_sentence = " ".join(["word"] * 500) + "."
    payloads: dict[str, SourcePayload] = {
        "guardian": {"url": "https://example.com", "text": giant_sentence}
    }
    chunker = NarrativeChunker()
    chunks = chunker.chunk(match_id=3869685, narratives=payloads)

    assert len(chunks) >= 2
    for c in chunks:
        words = c.text.split()
        assert len(words) <= 300
