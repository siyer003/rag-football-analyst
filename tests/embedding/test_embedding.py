import os
from unittest.mock import MagicMock, patch

import pytest

from footballanalyst.embedding.base import EmbeddingModel
from footballanalyst.embedding.factory import EmbeddingModelFactory, get_embedding_model
from footballanalyst.embedding.gemini import GeminiEmbedding
from footballanalyst.embedding.sentence_transformer import SentenceTransformerEmbedding
from tests.fakes import FakeEmbeddingModel


def test_fake_embedding_model_dimension_and_embed() -> None:
    fake = FakeEmbeddingModel(dimension=384)
    assert fake.dimension == 384
    embeddings = fake.embed(["test paragraph", "another text"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    assert len(embeddings[1]) == 384
    assert all(val == 0.0 for val in embeddings[0])


def test_fake_embedding_model_satisfies_protocol() -> None:
    fake: EmbeddingModel = FakeEmbeddingModel()
    assert fake.dimension == 384


def test_factory_returns_sentence_transformer_by_default() -> None:
    with patch.dict(os.environ, {}, clear=True):
        model = EmbeddingModelFactory.create()
        assert isinstance(model, SentenceTransformerEmbedding)
        assert isinstance(get_embedding_model(), SentenceTransformerEmbedding)


def test_factory_returns_gemini_model_when_requested() -> None:
    with patch.dict(os.environ, {"EMBEDDING_MODEL": "gemini"}):
        model = EmbeddingModelFactory.create()
        assert isinstance(model, GeminiEmbedding)


def test_sentence_transformer_embedding_embed_returns_floats() -> None:
    model = SentenceTransformerEmbedding()
    assert model.dimension == 384
    embeddings = model.embed(["hello"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384
    assert isinstance(embeddings[0][0], float)


def test_sentence_transformer_embedding_dimension_does_not_load_model() -> None:
    st = SentenceTransformerEmbedding()
    assert st._model is None
    assert st.dimension == 384
    assert st._model is None


def test_sentence_transformer_embedding_custom_model_dimension() -> None:
    st = SentenceTransformerEmbedding(model_name="all-mpnet-base-v2")
    assert st._model is None
    assert st.dimension == 768
    assert st._model is None


def test_sentence_transformer_embedding_empty_list() -> None:
    model = SentenceTransformerEmbedding()
    assert model.embed([]) == []


def test_gemini_embedding_raises_without_api_key() -> None:
    gemini = GeminiEmbedding()
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(ValueError, match="GOOGLE_API_KEY"),
    ):
        gemini.embed(["hello"])


def test_gemini_embedding_embeds_texts_with_api_key() -> None:
    gemini = GeminiEmbedding()
    mock_client = MagicMock()
    mock_emb1 = MagicMock()
    mock_emb1.values = [0.1, 0.2]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_emb1]
    mock_client.models.embed_content.return_value = mock_response

    with (
        patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}),
        patch("google.genai.Client", return_value=mock_client),
    ):
        res = gemini.embed(["hello"])
        assert res == [[0.1, 0.2]]
        mock_client.models.embed_content.assert_called_once_with(
            model="text-embedding-004",
            contents=["hello"],
        )


def test_gemini_embedding_empty_list() -> None:
    gemini = GeminiEmbedding()
    assert gemini.embed([]) == []
