import sys

import streamlit as st

from footballanalyst.app.ask import ask
from footballanalyst.app.types import Answer
from footballanalyst.corpus.registry import MatchRegistry
from footballanalyst.embedding.factory import EmbeddingModelFactory
from footballanalyst.generation import LLMProvider
from footballanalyst.generation.factory import LLMProviderFactory
from footballanalyst.retrieval import (
    EventRetriever,
    HybridRetriever,
    NarrativeRetriever,
)
from footballanalyst.store.vector_store import VectorStore


@st.cache_resource
def get_registry() -> MatchRegistry:
    return MatchRegistry.load()


@st.cache_resource
def get_retriever() -> HybridRetriever | None:
    try:
        embedding_model = EmbeddingModelFactory.create()
        store = VectorStore()
        event_retriever = EventRetriever(store)
        narrative_retriever = NarrativeRetriever(store)
        return HybridRetriever(
            event_retriever=event_retriever,
            narrative_retriever=narrative_retriever,
            embedding_model=embedding_model,
        )
    except Exception:
        return None


@st.cache_resource
def get_llm() -> LLMProvider | None:
    try:
        return LLMProviderFactory.create()
    except Exception:
        return None


def main() -> None:
    st.set_page_config(page_title="Football Analyst", page_icon="⚽")
    st.title("⚽ Football Analyst")
    st.caption(
        "A tactical-analysis assistant answering match strategy "
        "questions grounded in match events and narratives."
    )

    registry = get_registry()
    match_tuples = registry.matches()

    selected_match_id = st.selectbox(
        "Select a Match",
        options=[mid for mid, _ in match_tuples],
        format_func=registry.label,
    )

    question = st.text_area(
        "Tactical Question",
        placeholder=(
            "e.g. Why did Croatia's midfield dominate England in the first half?"
        ),
    )

    if st.button("Ask"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                try:
                    retriever = get_retriever()
                    llm = get_llm()
                    ans = ask(
                        query=question,
                        match_id=selected_match_id,
                        retriever=retriever,
                        llm=llm,
                        registry=registry,
                    )
                    st.session_state["last_answer"] = ans
                except Exception as err:
                    st.error(f"Error answering question: {err}")

    if "last_answer" in st.session_state:
        answer: Answer = st.session_state["last_answer"]
        st.subheader("Answer")
        st.markdown(answer.text)

        if answer.out_of_corpus:
            st.info("Match data for this query is not available in the corpus.")
        elif answer.citations:
            with st.expander("Sources"):
                for cite in answer.citations:
                    st.markdown(
                        f"**{cite.source}** (`{cite.chunk_type}`)\n\n> {cite.snippet}"
                    )


def run_cli() -> None:
    """CLI entry point to launch Streamlit application."""
    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", __file__]
    stcli.main()


if __name__ == "__main__":
    main()
