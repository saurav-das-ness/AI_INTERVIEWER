"""Retrieval service backed by ChromaDB with lexical fallback ranking."""

from __future__ import annotations

import re

from app.models.domain.content import QuestionContext
from app.providers.vector_store import ChromaContextVectorStore, VectorStoreError
from app.repositories.content_repository import SqliteContentRepository


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")


class RetrievalService:
    """Provides grounded context retrieval from approved topic and question context records."""

    def __init__(
        self,
        content_repository: SqliteContentRepository,
        vector_store: ChromaContextVectorStore,
    ) -> None:
        self._content_repository = content_repository
        self._vector_store = vector_store

    def index_contexts(self, contexts: list[QuestionContext]) -> None:
        """Index approved context records in ChromaDB."""

        if contexts:
            self._vector_store.upsert_contexts(contexts)

    def retrieve(
        self,
        topic_id: str,
        question_id: str,
        query_text: str,
        limit: int = 3,
        allowed_source_types: set[str] | None = None,
    ) -> list[dict[str, object]]:
        """Return ranked evidence references for a question and query text."""

        contexts = self._content_repository.list_contexts(topic_id=topic_id, question_id=question_id, published_only=True)
        contexts = _select_scope_contexts(contexts, question_id)
        filtered_contexts = (
            [context for context in contexts if context.source_type in allowed_source_types]
            if allowed_source_types
            else contexts
        )
        allowed_context_ids = {context.id for context in filtered_contexts}
        if not allowed_context_ids:
            return []

        try:
            evidence = self._vector_store.similarity_search(
                query_text=query_text,
                topic_id=topic_id,
                allowed_context_ids=allowed_context_ids,
                limit=limit,
            )
            if evidence:
                return _rerank_by_query_overlap(evidence, query_text, limit)
        except VectorStoreError:
            pass

        query_tokens = _tokenize(query_text)
        ranked: list[tuple[float, QuestionContext]] = []

        for context in filtered_contexts:
            context_tokens = _tokenize(context.context_text)
            if not context_tokens or not query_tokens:
                score = 0.0
            else:
                # Symmetric Jaccard gives a better semantic proxy than one-sided overlap,
                # which inflates scores for very short queries hitting large chunks.
                intersection = len(query_tokens & context_tokens)
                score = intersection / len(query_tokens | context_tokens)
            ranked.append((score, context))

        ranked.sort(key=lambda item: (item[0], item[1].priority), reverse=True)
        selected = ranked[:limit] if ranked else []
        return [
            {
                "evidence_id": f"EV_{index}",
                "context_id": context.id,
                "context_code": context.context_code,
                "source_type": context.source_type,
                "source_label": context.context_title,
                "excerpt": context.context_text[:240],
                "page_reference": context.page_reference,
                "relevance_score": round(score, 4),
            }
            for index, (score, context) in enumerate(selected, start=1)
        ]


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _select_scope_contexts(contexts: list[QuestionContext], question_id: str) -> list[QuestionContext]:
    """Prefer contexts linked to the active question to prevent cross-PDF leakage."""

    question_linked = [context for context in contexts if context.question_id == question_id]
    if not question_linked:
        return contexts

    question_linked_reference = [context for context in question_linked if context.source_type != "question"]
    if question_linked_reference:
        question_seed = [context for context in question_linked if context.source_type == "question"]
        return question_linked_reference + question_seed

    return question_linked


def _rerank_by_query_overlap(
    evidence: list[dict[str, object]],
    query_text: str,
    limit: int,
) -> list[dict[str, object]]:
    """Boost question-relevant chunks using lexical overlap over excerpts."""

    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return evidence[:limit]

    scored: list[tuple[float, dict[str, object]]] = []
    for item in evidence:
        excerpt_tokens = _tokenize(str(item.get("excerpt", "")))
        if excerpt_tokens:
            overlap = len(query_tokens & excerpt_tokens) / len(query_tokens | excerpt_tokens)
        else:
            overlap = 0.0
        vector_score = float(item.get("relevance_score", 0.0))
        hybrid = (0.7 * overlap) + (0.3 * vector_score)
        scored.append((hybrid, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [item for _, item in scored[:limit]]
    for index, item in enumerate(selected, start=1):
        item["evidence_id"] = f"EV_{index}"
    return selected
