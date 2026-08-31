"""Focused tests for evaluation logic and follow-up branching."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.domain.content import Question, RubricCriterion, WeightConfig
from app.providers.bedrock import LocalFeedbackProvider
from app.providers.vector_store import ChromaContextVectorStore
from app.repositories.content_repository import SqliteContentRepository
from app.services.evaluation.service import EvaluationService
from app.services.retrieval.service import RetrievalService


class EvaluationServiceTests(unittest.TestCase):
    """Business-rule tests for candidate scoring and mid-confidence branching."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp_dir.cleanup)
        base_path = Path(temp_dir.name)
        db_path = str(base_path / "test.db")
        repository = SqliteContentRepository(db_path)
        retrieval_service = RetrievalService(
            repository,
            ChromaContextVectorStore(
                persist_directory=str(base_path / "chroma"),
                collection_name="test_context",
                aws_region=None,
                bedrock_embedding_model_id="amazon.titan-embed-text-v2:0",
            ),
        )
        self.evaluation_service = EvaluationService(retrieval_service, LocalFeedbackProvider())
        self.question = Question(
            id="question-1",
            topic_id="topic-1",
            question_code="Q1",
            question_text="Explain idempotency",
            question_type="technical",
            difficulty="medium",
            expected_answer_summary="Discuss idempotency keys duplicate handling and persistence safety",
            followup_enabled=True,
            published=True,
            prompt_notes=None,
            time_limit_seconds=None,
            tags=[],
            language=None,
            source_reference=None,
        )
        self.rubric = [
            RubricCriterion(
                id="criterion-1",
                question_id="question-1",
                criterion_code="CR1",
                criterion_name="Accuracy",
                criterion_description="Discuss idempotency keys duplicate handling and persistence safety",
                weight=1.0,
                min_score=0.0,
                max_score=5.0,
                evidence_required=True,
            )
        ]
        self.weights = WeightConfig(
            id="weights-1",
            question_id="question-1",
            confidence_low=0.2,
            confidence_mid_start=0.4,
            confidence_mid_end=0.75,
            confidence_high=0.8,
            max_followups=3,
        )

    def test_incomplete_answer_triggers_followup(self) -> None:
        result = self.evaluation_service.evaluate_answer(
            session_id="session-1",
            answer_id="answer-1",
            topic_id="topic-1",
            question=self.question,
            rubric_criteria=self.rubric,
            weight_config=self.weights,
            answer_text="It avoids duplicates.",
            final_version=False,
        )
        self.assertFalse(result.followup_required)

    def test_mid_confidence_answer_triggers_followup(self) -> None:
        # 4 of 8 rubric keywords matched → LocalFeedbackProvider scores this as mid (0.5)
        result = self.evaluation_service.evaluate_answer(
            session_id="session-1",
            answer_id="answer-1",
            topic_id="topic-1",
            question=self.question,
            rubric_criteria=self.rubric,
            weight_config=self.weights,
            answer_text="Use idempotency keys for duplicate request handling",
            final_version=False,
        )
        self.assertTrue(result.followup_required)

    def test_followup_enriched_answer_finalizes(self) -> None:
        # max_followups=1: after 1 followup text is provided the limit is reached and must finalize
        weights_one = WeightConfig(
            id="weights-1",
            question_id="question-1",
            confidence_low=0.2,
            confidence_mid_start=0.4,
            confidence_mid_end=0.75,
            confidence_high=0.8,
            max_followups=1,
        )
        result = self.evaluation_service.evaluate_answer(
            session_id="session-1",
            answer_id="answer-1",
            topic_id="topic-1",
            question=self.question,
            rubric_criteria=self.rubric,
            weight_config=weights_one,
            answer_text="Use idempotency keys and duplicate checks.",
            followup_texts=["Store the key with persistence safeguards and replay the saved response."],
            final_version=True,
        )
        self.assertFalse(result.followup_required)
        self.assertEqual(result.evaluation.finalize_decision, "finalize")


if __name__ == "__main__":
    unittest.main()
