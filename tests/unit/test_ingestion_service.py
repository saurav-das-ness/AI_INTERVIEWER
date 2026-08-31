"""Focused tests for admin ingestion flows."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.schemas.admin import TopicPackageImportModel
from app.providers.file_storage import LocalFileStorage
from app.providers.vector_store import ChromaContextVectorStore
from app.repositories.content_repository import SqliteContentRepository
from app.services.ingestion.service import IngestionService
from app.services.retrieval.service import RetrievalService


class IngestionServiceTests(unittest.TestCase):
    """Business-rule tests for JSON and CSV imports."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp_dir.cleanup)
        base_path = Path(temp_dir.name)
        db_path = str(base_path / "test.db")
        repository = SqliteContentRepository(db_path)
        self.repository = repository
        retrieval_service = RetrievalService(
            repository,
            ChromaContextVectorStore(
                persist_directory=str(base_path / "chroma"),
                collection_name="test_context",
                aws_region=None,
                bedrock_embedding_model_id="amazon.titan-embed-text-v2:0",
            ),
        )
        self.service = IngestionService(repository, retrieval_service, LocalFileStorage(str(base_path / "uploads")))

    def test_preview_json_package_accepts_valid_payload(self) -> None:
        package = TopicPackageImportModel.model_validate(
            {
                "topic": {
                    "topic_code": "TOPIC_1",
                    "topic_name": "Topic One",
                    "description": "Test topic",
                    "published": True,
                },
                "questions": [
                    {
                        "question_code": "Q1",
                        "question_text": "Explain idempotency",
                        "question_type": "technical",
                        "difficulty": "medium",
                        "expected_answer_summary": "Discuss idempotency keys and duplicate handling",
                        "followup_enabled": True,
                        "max_followups": 3,
                        "confidence_thresholds": {"low": 0.2, "mid_start": 0.4, "mid_end": 0.7, "high": 0.8},
                        "rubric": [
                            {
                                "criterion_code": "CR1",
                                "criterion_name": "Accuracy",
                                "criterion_description": "Discuss idempotency keys",
                                "weight": 1.0,
                                "min_score": 0,
                                "max_score": 5,
                                "evidence_required": True,
                            }
                        ],
                    }
                ],
                "contexts": [],
            }
        )
        preview = self.service.preview_json_package(package)
        self.assertTrue(preview.valid)

    def test_apply_csv_text_creates_topic_and_questions(self) -> None:
        csv_text = (
            "topic_code,topic_name,question_code,question_text,question_type,difficulty,expected_answer_summary,followup_enabled,max_followups,confidence_low,confidence_mid_start,confidence_mid_end,confidence_high,published\n"
            "TOPIC_2,Topic Two,Q2,Explain retries,technical,medium,Discuss retry safety,true,2,0.2,0.4,0.7,0.8,true\n"
        )
        result = self.service.apply_csv_text(csv_text, "admin-user-id")
        self.assertEqual(result.question_count, 1)
        self.assertEqual(result.context_count, 1)

        topic = self.repository.get_topic_by_code("TOPIC_2")
        assert topic is not None
        question = self.repository.get_question_by_code("Q2")
        assert question is not None
        contexts = self.repository.list_contexts(topic_id=topic.id, question_id=question.id, published_only=True)
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0].source_type, "question")
        self.assertEqual(contexts[0].context_text, "Explain retries")

    def test_preview_counts_question_text_chunks(self) -> None:
        long_question = (
            "Explain the complete design of a distributed checkout system including stateless APIs, "
            "idempotency guarantees, caching trade-offs, consistency boundaries, async event processing, "
            "failure handling, observability pipelines, and cost-aware scaling policies across regions. "
            "Also discuss deployment topology and data partitioning details for sustained peak traffic scenarios."
        )
        csv_text = (
            "topic_code,topic_name,question_code,question_text,question_type,difficulty,expected_answer_summary,followup_enabled,max_followups,confidence_low,confidence_mid_start,confidence_mid_end,confidence_high,published\n"
            f'TOPIC_3,Topic Three,Q3,"{long_question}",technical,hard,Reference answer,true,2,0.2,0.4,0.7,0.8,true\n'
        )
        preview = self.service.preview_csv_text(csv_text)
        self.assertGreaterEqual(preview.context_count, 2)

    def test_preview_rejects_existing_question_code(self) -> None:
        first_csv = (
            "topic_code,topic_name,question_code,question_text,question_type,difficulty,expected_answer_summary,followup_enabled,max_followups,confidence_low,confidence_mid_start,confidence_mid_end,confidence_high,published\n"
            "TOPIC_10,Topic Ten,Q_DUP,Explain retries,technical,medium,Discuss retry safety,true,2,0.2,0.4,0.7,0.8,true\n"
        )
        self.service.apply_csv_text(first_csv, "admin-user-id")

        second_csv = (
            "topic_code,topic_name,question_code,question_text,question_type,difficulty,expected_answer_summary,followup_enabled,max_followups,confidence_low,confidence_mid_start,confidence_mid_end,confidence_high,published\n"
            "TOPIC_11,Topic Eleven,Q_DUP,Explain idempotency,technical,medium,Discuss duplicate safety,true,2,0.2,0.4,0.7,0.8,true\n"
        )
        preview = self.service.preview_csv_text(second_csv)
        self.assertFalse(preview.valid)
        self.assertTrue(any("already exists" in m.message for m in preview.messages))


if __name__ == "__main__":
    unittest.main()
