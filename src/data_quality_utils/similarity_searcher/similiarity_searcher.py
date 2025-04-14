from typing import Literal, get_args

import numpy as np
import polars as pl
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer, util

_STRATEGIES = Literal["document", "chunk", "best_of_three"]
DEFAULT_SEPARATORS = ["##", "\n\n", ". ", " ", ""]


class SimilaritySearcher:
    """An embedding based search class which checks a
    series of markdown texts against a prompt to find the best
    match.

    :param strategy: One of "document", "chunk", "best_of_three",
    determines whether the similarity match is the closest document, closest chunk of
    a document, or document with the highest average for the top three chunks.
    """

    def __init__(
        self,
        strategy: _STRATEGIES,
        chunk_size=500,
        chunk_overlap=75,
        separators: list[str] = DEFAULT_SEPARATORS,
        keep_chunk_separators=False,
    ):
        if strategy not in get_args(_STRATEGIES):
            raise ValueError("strategy must be one of {_STRATEGIES}")
        self.strategy = strategy
        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_separators = separators
        self.keep_chunk_separators = keep_chunk_separators

    def search(
        self,
        query: str,
        document_df: pl.DataFrame,
        keyword_filters: None | list[str] = None,
    ) -> pl.DataFrame:
        """Find best matching document based on embeddings.

        :param query: Text to compare documents to, documents are ranked by embedding
            similarity
        :param documents: DataFrame with id and text columns
        :param keyword_filters: List of strings which documents must contain to be
            included in search, defaults to None
        :return: id and similarity score of each document.
        """
        document_df = self._filter_documents(
            document_df=document_df, keyword_filters=keyword_filters
        )

        # catch times all documents are filtered
        if len(document_df) == 0:
            return document_df

        # embed documents and the prompt for comparison
        document_df = self._embed_documents(document_df)
        query_embedding = self.embedding_model.encode(query)

        # get similarity scores
        document_df = document_df.with_columns(
            similarity=util.cos_sim(
                query_embedding, np.stack(document_df["embedding"].to_numpy())  # type: ignore
            )
            .numpy()
            .flatten()
        )  # type: ignore

        if self.strategy == "document":
            return document_df[["id", "similarity"]].sort(
                by="similarity", descending=True
            )
        if self.strategy == "chunk":
            return (
                document_df.group_by("id")
                .agg(pl.max("similarity"))
                .sort(by="similarity", descending=True)
            )
        else:
            return (
                document_df.group_by("id")
                .agg(pl.map_groups(exprs="similarity", function=self._top_three))
                .sort(by="similarity", descending=True)
            )

    def _filter_documents(
        self, document_df: pl.DataFrame, keyword_filters: None | list[str] = None
    ) -> pl.DataFrame:
        """Remove documents without text and optionally remove documents where the text
        does not contain all of the words in a list of keywords

        :param document_df: Documents in dataframe of id,text columns.
        :param keyword_filters: List of words that must be in documents, defaults to None
        :return: Documents that have text and optionally contain all keywords.
        """
        filter = document_df["text"].is_not_null()
        if keyword_filters:
            for keyword in keyword_filters:
                filter = filter & (
                    document_df["text"].str.to_lowercase().str.contains(keyword.lower())
                )
        return document_df.filter(filter)

    def _embed_documents(self, document_df: pl.DataFrame) -> pl.DataFrame:
        """Chunk and embed documents as appropriate for the search strategy chosen
        at initialisation.

        :param document_df:  Documents in dataframe of id,text columns.
        :return: Dataframe with text column replaced by chunks and a column added
            for embeddings.
        """
        if self.strategy != "document":
            df = document_df.with_columns(
                text=document_df["text"].map_elements(self._split_text)
            )
            df = df.explode("text")
        else:
            df = document_df[["id", "text"]]

        df = df.with_columns(
            embedding=df["text"].map_elements(self.embedding_model.encode)
        )
        return df

    def _split_text(self, text: str) -> list[str]:
        """Split text, preferring to split at separator
        characters.

        :param text: Text to split into chunks
        :return: list of chunks.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.chunk_separators,
            keep_separator=self.keep_chunk_separators,
        )

        chunks = text_splitter.split_text(text)
        return chunks

    def _top_three(self, similarities):
        """Returns mean of top 3 of a group of similarities."""
        similarities = similarities[0].sort(descending=True)
        return similarities[:3].mean()
