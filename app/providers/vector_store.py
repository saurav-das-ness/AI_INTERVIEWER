"""LangChain and ChromaDB-backed vector store for approved interview context."""

from __future__ import annotations

import hashlib
import math
import re

import boto3
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.models.domain.content import QuestionContext


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")


class VectorStoreError(RuntimeError):
    """Raised when vector indexing or retrieval fails."""


class LocalHashEmbeddings(Embeddings):
    """Deterministic local embeddings used when Bedrock credentials are unavailable."""

    def __init__(self, dimensions: int = 96) -> None:
        self._dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        vector = [0.0] * self._dimensions
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self._dimensions):
                vector[index] += digest[index % len(digest)] / 255.0

        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]


class ChromaContextVectorStore:
    """Manage approved context chunks in a Chroma collection through LangChain."""

    def __init__(
        self,
        *,
        persist_directory: str,
        collection_name: str,
        aws_region: str | None,
        bedrock_embedding_model_id: str,
    ) -> None:
        self._persist_directory = persist_directory
        self._collection_name = collection_name
        self._aws_region = aws_region
        self._bedrock_embedding_model_id = bedrock_embedding_model_id
        self._embedding_function = self._build_embeddings()
        self._store = Chroma(
            collection_name=self._collection_name,
            persist_directory=self._persist_directory,
            embedding_function=self._embedding_function,
        )

    def upsert_contexts(self, contexts: list[QuestionContext]) -> None:
        """Index or refresh approved context records in Chroma."""

        if not contexts:
            return

        ids = [context.id for context in contexts]
        documents = [
            Document(
                page_content=context.context_text,
                metadata={
                    "context_id": context.id,
                    "context_code": context.context_code,
                    "topic_id": context.topic_id,
                    "question_id": context.question_id or "",
                    "source_type": context.source_type,
                    "context_title": context.context_title,
                    "storage_ref": context.storage_ref or "",
                    "page_reference": context.page_reference or "",
                    "section_reference": context.section_reference or "",
                    "priority": context.priority,
                    "published": context.published,
                },
            )
            for context in contexts
        ]

        try:
            self._store.delete(ids=ids)
        except Exception:
            pass

        try:
            self._store.add_documents(documents=documents, ids=ids)
        except Exception as exc:
            raise VectorStoreError("Unable to index context chunks in ChromaDB") from exc

    def similarity_search(
        self,
        *,
        query_text: str,
        topic_id: str,
        allowed_context_ids: set[str],
        limit: int,
    ) -> list[dict[str, object]]:
        """Search the Chroma collection and return provenance-rich evidence entries."""

        if not allowed_context_ids:
            return []

        try:
            matches = self._store.similarity_search_with_relevance_scores(
                query_text,
                k=max(limit * 4, limit),
                filter={"topic_id": topic_id},
            )
        except Exception as exc:
            raise VectorStoreError("Unable to query ChromaDB for grounded context") from exc

        evidence: list[dict[str, object]] = []
        for index, (document, score) in enumerate(matches, start=1):
            context_id = str(document.metadata.get("context_id", ""))
            if context_id not in allowed_context_ids:
                continue
            evidence.append(
                {
                    "evidence_id": f"EV_{index}",
                    "context_id": context_id,
                    "context_code": str(document.metadata.get("context_code", "")),
                    "source_type": str(document.metadata.get("source_type", "")),
                    "source_label": str(document.metadata.get("context_title", "")),
                    "excerpt": document.page_content[:240],
                    "page_reference": str(document.metadata.get("page_reference", "")) or None,
                    "relevance_score": round(float(score), 4),
                }
            )
            if len(evidence) >= limit:
                break

        return evidence

    def _build_embeddings(self) -> Embeddings:
        if self._aws_region and _has_aws_credentials(self._aws_region):
            return BedrockEmbeddings(
                model_id=self._bedrock_embedding_model_id,
                region_name=self._aws_region,
            )
        return LocalHashEmbeddings()


def _has_aws_credentials(region_name: str) -> bool:
    session = boto3.Session(region_name=region_name)
    credentials = session.get_credentials()
    return credentials is not None
