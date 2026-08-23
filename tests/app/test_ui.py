from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import footballanalyst.app.ui  # noqa: F401
from footballanalyst.app.types import Answer, ChunkRef

UI_FILE = str(Path(__file__).parents[2] / "src" / "footballanalyst" / "app" / "ui.py")


def test_ui_shows_spinner_placeholder_before_question() -> None:
    """App renders without error on cold load."""
    at = AppTest.from_file(UI_FILE, default_timeout=10).run()
    assert not at.exception


def test_ui_renders_match_selector() -> None:
    """Assert a selectbox with at least 8 options is present."""
    at = AppTest.from_file(UI_FILE, default_timeout=10).run()
    assert not at.exception
    assert len(at.selectbox) >= 1
    selectbox = at.selectbox[0]
    assert len(selectbox.options) >= 8


def test_ui_submitting_question_displays_answer_and_citations() -> None:
    """Submitting question calls ask() and renders answer and citations expander."""
    fake_answer = Answer(
        text="Liverpool pressed aggressively in the first half.",
        citations=[
            ChunkRef(
                chunk_id="chk1",
                source="statsbomb",
                chunk_type="event_summary",
                snippet="High press in 4-3-3 shape.",
            )
        ],
        out_of_corpus=False,
    )

    with patch("footballanalyst.app.ask.ask", return_value=fake_answer):
        at = AppTest.from_file(UI_FILE, default_timeout=10).run()
        at.text_area[0].input("Why did Liverpool press?")
        at.button[0].click().run()
        assert not at.exception
        assert any(
            "Liverpool pressed aggressively in the first half." in str(m.value)
            for m in at.markdown
        )


def test_ui_submitting_out_of_corpus_displays_info_message() -> None:
    """Submitting an out-of-corpus match displays info message instead of citations."""
    fake_answer = Answer(
        text="Match ID 9999 is not in corpus.",
        citations=[],
        out_of_corpus=True,
    )

    with patch("footballanalyst.app.ask.ask", return_value=fake_answer):
        at = AppTest.from_file(UI_FILE, default_timeout=10).run()
        at.text_area[0].input("Out of corpus query")
        at.button[0].click().run()
        assert not at.exception
        assert len(at.info) >= 1


def test_ui_handles_ask_exceptions_gracefully() -> None:
    """Exceptions raised during ask() display st.error instead of tracebacks."""
    with patch("footballanalyst.app.ask.ask", side_effect=RuntimeError("API error")):
        at = AppTest.from_file(UI_FILE, default_timeout=10).run()
        at.text_area[0].input("Error test query")
        at.button[0].click().run()
        assert not at.exception
        assert len(at.error) >= 1
        assert "API error" in at.error[0].value
