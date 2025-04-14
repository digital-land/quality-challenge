import numpy as np
import polars as pl

from data_quality_utils.similarity_searcher import (
    SimilaritySearcher,
    similiarity_searcher,
)


class MockEncoder:
    def __init__(self, model):
        pass

    def encode(self, encode_str: str) -> np.ndarray:
        return np.asarray([encode_str.count(letter) for letter in "abc"], dtype=float)


# patch encoder
similiarity_searcher.SentenceTransformer = MockEncoder  # type:ignore


def test_empty():
    searcher = SimilaritySearcher(strategy="document")
    searcher.search("abc", pl.DataFrame(schema=["id", "text"]))


def test_null_text():
    searcher = SimilaritySearcher(strategy="document")
    df = pl.DataFrame(
        data=[["1", "2", "3", "4"], ["aa", None, "b", "c"]], schema=["id", "text"]
    )
    assert len(searcher.search(query="aa", document_df=df)) == 3


def test_keyword_filter():
    searcher = SimilaritySearcher(strategy="document")
    df = pl.DataFrame(
        data=[["1", "2", "3", "4"], ["aa", None, "b", "c"]], schema=["id", "text"]
    )
    assert len(searcher.search(query="aa", document_df=df, keyword_filters=["b"])) == 1
