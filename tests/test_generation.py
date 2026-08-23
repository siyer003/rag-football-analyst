"""Tests for the generation package: prompt assembly, citations, providers."""

import pytest

from footballanalyst.generation.citations import parse_citations
from footballanalyst.generation.factory import LLMProviderFactory
from footballanalyst.generation.prompt import build_prompt
from footballanalyst.ingestion.types import EventSummary, NarrativeChunk
from footballanalyst.retrieval.types import RankedChunk, RetrievedContext
from tests.fakes import FakeLLMProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event_chunk(n: int) -> RankedChunk:
    chunk = EventSummary(
        match_id=22912,
        window="first_15_min",
        text=f"Event text {n}",
        chunk_id=f"evt-{n:03d}",
        chunk_type="event_summary",
        source="statsbomb",
    )
    return RankedChunk(chunk=chunk, rrf_score=1.0 / n, rank=n)


def make_narrative_chunk(n: int) -> RankedChunk:
    chunk = NarrativeChunk(
        match_id=22912,
        source="guardian",
        url="https://guardian.com/match",
        text=f"Narrative text {n}",
        chunk_id=f"nar-{n:03d}",
        chunk_type="narrative",
    )
    return RankedChunk(chunk=chunk, rrf_score=1.0 / (n + 10), rank=n + 10)


# ---------------------------------------------------------------------------
# Cycle 1: build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_returns_two_non_empty_strings() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1), make_narrative_chunk(1)])
    system, user = build_prompt("Why did Klopp press high?", context)
    assert isinstance(system, str) and len(system) > 0
    assert isinstance(user, str) and len(user) > 0


def test_build_prompt_user_prompt_contains_chunk_text() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    _, user = build_prompt("Test query", context)
    assert "Event text 1" in user


def test_build_prompt_user_prompt_contains_query() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    _, user = build_prompt("Why did Klopp press high?", context)
    assert "Why did Klopp press high?" in user


def test_build_prompt_user_prompt_numbers_chunks_from_1() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1), make_event_chunk(2)])
    _, user = build_prompt("Query", context)
    assert "[1]" in user
    assert "[2]" in user


def test_build_prompt_user_prompt_includes_source() -> None:
    context = RetrievedContext(chunks=[make_narrative_chunk(1)])
    _, user = build_prompt("Query", context)
    assert "guardian" in user


def test_build_prompt_system_prompt_instructs_citation() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    system, _ = build_prompt("Query", context)
    assert "[N]" in system or "cite" in system.lower()


def test_build_prompt_system_prompt_instructs_not_enough_info() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    system, _ = build_prompt("Query", context)
    assert "not enough information" in system.lower()


def test_build_prompt_system_prompt_forbids_inferring_event_manner_details() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    system, _ = build_prompt("Query", context)
    assert (
        "header" in system
        or "method/manner" in system
        or "how an event occurred" in system
    )


def test_build_prompt_empty_context_still_returns_strings() -> None:
    context = RetrievedContext(chunks=[])
    system, user = build_prompt("Query", context)
    assert isinstance(system, str) and len(system) > 0
    assert isinstance(user, str) and len(user) > 0


# ---------------------------------------------------------------------------
# Cycle 2: parse_citations
# ---------------------------------------------------------------------------


def test_parse_citations_extracts_valid_chunk_ref() -> None:

    context = RetrievedContext(chunks=[make_event_chunk(1), make_narrative_chunk(1)])
    refs = parse_citations("Liverpool pressed high [1] and held shape [2].", context)
    assert len(refs) == 2
    assert refs[0].chunk_id == "evt-001"
    assert refs[1].chunk_id == "nar-001"


def test_parse_citations_returns_correct_chunk_ref_fields() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    refs = parse_citations("Evidence for [1].", context)
    assert len(refs) == 1
    ref = refs[0]
    assert ref.source == "statsbomb"
    assert ref.chunk_type == "event_summary"
    assert "Event text 1" in ref.snippet


def test_parse_citations_drops_out_of_range_index() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])  # only index [1] is valid
    refs = parse_citations("See [1] and [9].", context)  # [9] out of range
    assert len(refs) == 1
    assert refs[0].chunk_id == "evt-001"


def test_parse_citations_no_citations_returns_empty_list() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    refs = parse_citations("No citations here.", context)
    assert refs == []


def test_parse_citations_deduplicates_repeated_citations() -> None:
    context = RetrievedContext(chunks=[make_event_chunk(1)])
    refs = parse_citations("[1] and again [1].", context)
    assert len(refs) == 1


def test_parse_citations_empty_context_returns_empty_list() -> None:
    context = RetrievedContext(chunks=[])
    refs = parse_citations("[1][2]", context)
    assert refs == []


# ---------------------------------------------------------------------------
# Cycle 3: FakeLLMProvider + LLMProviderFactory
# ---------------------------------------------------------------------------


def test_fake_llm_provider_complete_returns_non_empty_string() -> None:

    llm = FakeLLMProvider()
    result = llm.complete(system="sys", user="usr")
    assert isinstance(result, str) and len(result) > 0


def test_fake_llm_provider_complete_contains_citation_marker() -> None:
    llm = FakeLLMProvider()
    result = llm.complete(system="sys", user="usr")
    assert "[1]" in result


def test_llm_provider_factory_defaults_to_groq(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    provider = LLMProviderFactory.create()
    assert type(provider).__name__ == "GroqProvider"


def test_llm_provider_factory_returns_gemini_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    provider = LLMProviderFactory.create()
    assert type(provider).__name__ == "GeminiProvider"


def test_groq_provider_raises_on_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from footballanalyst.generation.groq_provider import GroqProvider, LLMConfigError

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMConfigError, match="GROQ_API_KEY"):
        GroqProvider()
