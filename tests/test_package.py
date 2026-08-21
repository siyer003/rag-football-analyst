import importlib

import pytest

SUBPACKAGES = [
    "footballanalyst.corpus",
    "footballanalyst.ingestion",
    "footballanalyst.retrieval",
    "footballanalyst.generation",
    "footballanalyst.embedding",
    "footballanalyst.store",
    "footballanalyst.app",
    "footballanalyst.eval",
]


def test_footballanalyst_package_imports() -> None:
    """Verify that footballanalyst top-level package can be imported."""
    pkg = importlib.import_module("footballanalyst")
    assert pkg is not None


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackages_import(subpackage: str) -> None:
    """Verify that all 8 subpackages can be imported."""
    mod = importlib.import_module(subpackage)
    assert mod is not None


def test_fakes_module_imports() -> None:
    """Verify that tests.fakes can be imported."""
    fakes = importlib.import_module("tests.fakes")
    assert fakes is not None
