import pytest

from footballanalyst.app.ask import ask
from footballanalyst.app.types import Answer
from footballanalyst.corpus.registry import MatchRegistry

V1_MATCH_IDS = [
    3869685,  # WC 2022 Final
    8658,  # WC 2018 Final
    8656,  # WC 2018 Semi
    3795506,  # Euro 2020 Final
    3943043,  # Euro 2024 Final
    22912,  # UCL 2018/2019 Final
    18245,  # UCL 2017/2018 Final
    3750201,  # UCL 2008/2009 Final
]


def test_registry_contains_all_v1_matches() -> None:
    registry = MatchRegistry.load()
    assert len(registry.match_ids()) == 8
    for match_id in V1_MATCH_IDS:
        assert registry.contains(match_id) is True
        assert (match_id in registry) is True
        assert isinstance(registry.label(match_id), str)

    assert registry.contains(99999) is False
    assert (99999 in registry) is False


def test_registry_fails_fast_on_malformed_entries() -> None:
    with pytest.raises(ValueError, match="missing 'match_id' or 'label'"):
        MatchRegistry([{"match_id": 12345}])  # missing label

    with pytest.raises(ValueError, match="missing 'match_id' or 'label'"):
        MatchRegistry([{"label": "Test Match"}])  # missing match_id

    with pytest.raises(ValueError, match="invalid match_id"):
        MatchRegistry([{"match_id": "not_an_int", "label": "Test Match"}])


def test_ask_returns_out_of_corpus_for_unknown_match_id() -> None:
    registry = MatchRegistry.load()
    answer: Answer = ask(
        query="Why did Argentina press high?",
        match_id=99999,
        retriever=None,
        llm=None,
        registry=registry,
    )
    assert answer.out_of_corpus is True
    assert answer.citations == []
    text_lower = answer.text.lower()
    assert "not in corpus" in text_lower or "available matches" in text_lower


# ---------------------------------------------------------------------------
# Happy path tests (Ticket 09)
# ---------------------------------------------------------------------------

from footballanalyst.ingestion.types import EventSummary
from footballanalyst.retrieval.types import RankedChunk, RetrievedContext
from tests.fakes import FakeHybridRetriever, FakeLLMProvider


def _make_context() -> RetrievedContext:
    """Build a minimal RetrievedContext with one EventSummary chunk."""
    chunk = EventSummary(
        match_id=22912,
        window="first_15_min",
        text="Liverpool pressed with intensity in the opening phase.",
        chunk_id="evt-001",
        chunk_type="event_summary",
        source="statsbomb",
    )
    return RetrievedContext(chunks=[RankedChunk(chunk=chunk, rrf_score=0.5, rank=1)])


def test_ask_calls_retriever_with_correct_match_id() -> None:
    retriever = FakeHybridRetriever(context=_make_context())
    ask(
        query="Why did Klopp's press work?",
        match_id=22912,
        retriever=retriever,
        llm=FakeLLMProvider(),
        registry=MatchRegistry.load(),
    )
    assert len(retriever.calls) == 1
    _, called_match_id = retriever.calls[0]
    assert called_match_id == 22912


def test_ask_returns_answer_with_text_and_citations() -> None:
    answer = ask(
        query="Why did Klopp's press work?",
        match_id=22912,
        retriever=FakeHybridRetriever(context=_make_context()),
        llm=FakeLLMProvider(),
        registry=MatchRegistry.load(),
    )
    assert answer.out_of_corpus is False
    assert len(answer.text) > 0
    assert len(answer.citations) > 0


def test_ask_answer_text_comes_from_llm() -> None:
    llm = FakeLLMProvider()
    answer = ask(
        query="Why did Klopp's press work?",
        match_id=22912,
        retriever=FakeHybridRetriever(context=_make_context()),
        llm=llm,
        registry=MatchRegistry.load(),
    )
    assert answer.text == llm.CANNED_RESPONSE


def test_ask_does_not_call_llm_for_out_of_corpus_match() -> None:
    class TrackingFakeLLM(FakeLLMProvider):
        called = False

        def complete(self, system: str, user: str) -> str:
            TrackingFakeLLM.called = True
            return super().complete(system, user)

    ask(
        query="Irrelevant",
        match_id=99999,
        retriever=FakeHybridRetriever(),
        llm=TrackingFakeLLM(),
        registry=MatchRegistry.load(),
    )
    assert TrackingFakeLLM.called is False

