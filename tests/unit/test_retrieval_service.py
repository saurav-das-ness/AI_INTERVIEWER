"""Focused tests for retrieval scoping and context selection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.providers.vector_store import ChromaContextVectorStore
from app.repositories.content_repository import SqliteContentRepository
from app.services.retrieval.service import RetrievalService


class RetrievalServiceTests(unittest.TestCase):
    """Ensure retrieval remains scoped to the intended question context."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp_dir.cleanup)
        base_path = Path(temp_dir.name)
        db_path = str(base_path / "test.db")

        self.repository = SqliteContentRepository(db_path)
        self.vector_store = ChromaContextVectorStore(
            persist_directory=str(base_path / "chroma"),
            collection_name="test_context",
            aws_region=None,
            bedrock_embedding_model_id="amazon.titan-embed-text-v2:0",
        )
        self.service = RetrievalService(self.repository, self.vector_store)

        self.topic = self.repository.create_topic(
            topic_code="TOPIC_SCOPE",
            topic_name="Topic Scope",
            description="Scope test",
            created_by="admin",
            published=True,
        )
        self.question_a = self.repository.create_question(
            topic_id=self.topic.id,
            question_code="Q_SCOPE_A",
            question_text="Explain idempotency keys",
            question_type="technical",
            difficulty="medium",
            expected_answer_summary="Idempotency keys and replay",
            followup_enabled=True,
            published=True,
            prompt_notes=None,
            time_limit_seconds=None,
            tags=[],
            language=None,
            source_reference=None,
        )
        self.question_b = self.repository.create_question(
            topic_id=self.topic.id,
            question_code="Q_SCOPE_B",
            question_text="Explain CAP theorem",
            question_type="technical",
            difficulty="medium",
            expected_answer_summary="Consistency availability partition tolerance",
            followup_enabled=True,
            published=True,
            prompt_notes=None,
            time_limit_seconds=None,
            tags=[],
            language=None,
            source_reference=None,
        )

    def test_question_linked_pdf_is_preferred_over_topic_level_pdf(self) -> None:
        question_context = self.repository.create_context(
            topic_id=self.topic.id,
            question_id=self.question_a.id,
            context_code="CTX_Q_A",
            source_type="pdf",
            context_title="Idempotency PDF",
            context_text="Idempotency keys let APIs replay persisted responses safely.",
            storage_ref="uploads/q_a.pdf",
            page_reference="page-1",
            section_reference=None,
            priority=1,
            published=True,
        )
        topic_context = self.repository.create_context(
            topic_id=self.topic.id,
            question_id=None,
            context_code="CTX_TOPIC",
            source_type="pdf",
            context_title="Generic Topic PDF",
            context_text="CAP theorem discusses consistency and partition tolerance.",
            storage_ref="uploads/topic.pdf",
            page_reference="page-2",
            section_reference=None,
            priority=1,
            published=True,
        )

        self.service.index_contexts([question_context, topic_context])

        evidence = self.service.retrieve(
            topic_id=self.topic.id,
            question_id=self.question_a.id,
            query_text="How do idempotency keys prevent duplicate charges?",
            limit=3,
            allowed_source_types={"pdf"},
        )

        context_ids = {str(item.get("context_id", "")) for item in evidence}
        self.assertIn(question_context.id, context_ids)
        self.assertNotIn(topic_context.id, context_ids)

    def test_question_without_linked_pdf_can_use_topic_level_pdf(self) -> None:
        topic_context = self.repository.create_context(
            topic_id=self.topic.id,
            question_id=None,
            context_code="CTX_TOPIC_ONLY",
            source_type="pdf",
            context_title="CAP PDF",
            context_text="CAP theorem describes trade-offs under partitions.",
            storage_ref="uploads/topic_only.pdf",
            page_reference="page-5",
            section_reference=None,
            priority=1,
            published=True,
        )
        self.service.index_contexts([topic_context])

        evidence = self.service.retrieve(
            topic_id=self.topic.id,
            question_id=self.question_b.id,
            query_text="Explain CAP theorem",
            limit=2,
            allowed_source_types={"pdf"},
        )

        context_ids = {str(item.get("context_id", "")) for item in evidence}
        self.assertIn(topic_context.id, context_ids)


if __name__ == "__main__":
    unittest.main()
