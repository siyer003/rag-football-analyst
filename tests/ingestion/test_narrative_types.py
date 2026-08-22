from footballanalyst.ingestion.types import NarrativeChunk, SourcePayload


def test_source_payload_typed_dict() -> None:
    payload: SourcePayload = {
        "url": "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Final",
        "text": "The 2022 FIFA World Cup Final was the final match...",
    }
    assert payload["url"] == "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Final"
    assert payload["text"].startswith("The 2022 FIFA World Cup")


def test_narrative_chunk_dataclass() -> None:
    chunk = NarrativeChunk(
        match_id=3869685,
        source="wikipedia",
        url="https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Final",
        text="Sample narrative text.",
        chunk_id="a1b2c3d4e5f67890",
    )
    assert chunk.match_id == 3869685
    assert chunk.chunk_type == "narrative"
    assert chunk.source == "wikipedia"
    assert chunk.url == "https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Final"
    assert chunk.text == "Sample narrative text."
    assert chunk.chunk_id == "a1b2c3d4e5f67890"
