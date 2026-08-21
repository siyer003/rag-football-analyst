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
