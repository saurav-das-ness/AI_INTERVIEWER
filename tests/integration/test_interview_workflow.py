"""Integration test for the first end-to-end interview workflow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.models.domain.user import UserRole
from app.models.schemas.admin import TopicPackageImportModel
from app.models.schemas.auth import RegisterRequest
from app.models.schemas.interview import SessionStartRequest, SubmitAnswerRequest, SubmitFollowupRequest
from app.providers.bedrock import LocalFeedbackProvider
from app.providers.file_storage import LocalFileStorage
from app.providers.vector_store import ChromaContextVectorStore
from app.repositories.content_repository import SqliteContentRepository
from app.repositories.interview_repository import SqliteInterviewRepository
from app.repositories.user_repository import SqliteUserRepository
from app.services.auth.service import AuthService
from app.services.evaluation.service import EvaluationService
from app.services.ingestion.service import IngestionService
from app.services.interview.service import InterviewService
from app.services.retrieval.service import RetrievalService


class InterviewWorkflowIntegrationTests(unittest.TestCase):
    """End-to-end test for import, session start, answer, follow-up, and finalization."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temp_dir.cleanup)
        base_path = Path(temp_dir.name)
        db_path = str(base_path / "test.db")

        self.user_repository = SqliteUserRepository(db_path)
        self.content_repository = SqliteContentRepository(db_path)
        self.interview_repository = SqliteInterviewRepository(db_path)
        self.auth_service = AuthService(self.user_repository)
        self.retrieval_service = RetrievalService(
            self.content_repository,
            ChromaContextVectorStore(
                persist_directory=str(base_path / "chroma"),
                collection_name="test_context",
                aws_region=None,
                bedrock_embedding_model_id="amazon.titan-embed-text-v2:0",
            ),
        )
        self.ingestion_service = IngestionService(
            self.content_repository,
            self.retrieval_service,
            LocalFileStorage(str(base_path / "uploads")),
        )
        self.evaluation_service = EvaluationService(self.retrieval_service, LocalFeedbackProvider())
        self.interview_service = InterviewService(
            auth_service=self.auth_service,
            content_repository=self.content_repository,
            interview_repository=self.interview_repository,
            evaluation_service=self.evaluation_service,
            retrieval_service=self.retrieval_service,
        )

    def test_candidate_can_complete_single_question_session_with_followup(self) -> None:
        admin = self.auth_service.register_user(
            RegisterRequest(email="admin@example.com", password="StrongPass123", role=UserRole.ADMIN)
        )
        candidate = self.auth_service.register_user(
            RegisterRequest(email="candidate@example.com", password="StrongPass123", role=UserRole.CANDIDATE)
        )

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
                        "expected_answer_summary": "Discuss idempotency keys duplicate handling persistence and replay behavior",
                        "followup_enabled": True,
                        "max_followups": 1,
                        "confidence_thresholds": {"low": 0.1, "mid_start": 0.2, "mid_end": 0.95, "high": 0.98},
                        "rubric": [
                            {
                                "criterion_code": "CR1",
                                "criterion_name": "Accuracy",
                                "criterion_description": "Discuss idempotency keys duplicate handling persistence and replay behavior",
                                "weight": 1.0,
                                "min_score": 0,
                                "max_score": 5,
                                "evidence_required": True,
                            }
                        ],
                    }
                ],
                "contexts": [
                    {
                        "context_code": "CTX1",
                        "scope_type": "question",
                        "scope_code": "Q1",
                        "context_title": "Idempotency reference",
                        "context_text": "Idempotency keys and replay responses help prevent duplicates and keep persistence safe.",
                        "source_type": "manual",
                        "published": True,
                    }
                ],
            }
        )
        imported = self.ingestion_service.apply_json_package(package, admin.id)
        session = self.interview_service.start_session(
            SessionStartRequest(candidate_id=candidate.id, topic_id=imported.topic_id)
        )
        self.assertGreaterEqual(len(session.question.grounding_chunks), 1)
        first_result = self.interview_service.submit_answer(
            SubmitAnswerRequest(
                session_id=session.session_id,
                question_id=session.question.id,
                answer_text="Use idempotency keys and duplicate handling in the API flow, but I would need more detail on persistence safety.",
            )
        )
        self.assertIsNotNone(first_result.followup)

        second_result = self.interview_service.submit_followup(
            SubmitFollowupRequest(
                session_id=session.session_id,
                followup_id=first_result.followup.followup_id,
                answer_text="Use idempotency keys, replay stored responses, and persist the key safely.",
            )
        )
        self.assertTrue(second_result.interview_complete)
        self.assertIsNotNone(second_result.evaluation)


if __name__ == "__main__":
    unittest.main()
