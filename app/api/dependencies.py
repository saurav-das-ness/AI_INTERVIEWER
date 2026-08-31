"""Shared dependency wiring for FastAPI routes."""

from app.core.settings import Settings, get_settings
from app.providers.bedrock import FeedbackProvider, RoutedFeedbackProvider
from app.providers.file_storage import LocalFileStorage
from app.providers.vector_store import ChromaContextVectorStore
from app.repositories.content_repository import ContentRepository, SqliteContentRepository
from app.repositories.interview_repository import InterviewRepository, SqliteInterviewRepository
from app.repositories.user_repository import SqliteUserRepository, UserRepository
from app.services.auth.service import AuthService
from app.services.evaluation.service import EvaluationService
from app.services.ingestion.service import IngestionService
from app.services.interview.service import InterviewService
from app.services.reporting.service import ReportingService
from app.services.retrieval.service import RetrievalService


def get_user_repository() -> UserRepository:
    settings = get_settings()
    return SqliteUserRepository(settings.sqlite_db_path)


def get_auth_service() -> AuthService:
    repository = get_user_repository()
    return AuthService(repository)


def get_content_repository() -> ContentRepository:
    settings = get_settings()
    return SqliteContentRepository(settings.sqlite_db_path)


def get_interview_repository() -> InterviewRepository:
    settings = get_settings()
    return SqliteInterviewRepository(settings.sqlite_db_path)


def get_file_storage() -> LocalFileStorage:
    settings = get_settings()
    return LocalFileStorage(settings.uploads_dir)


def get_vector_store() -> ChromaContextVectorStore:
    settings = get_settings()
    return ChromaContextVectorStore(
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
        aws_region=settings.aws_region,
        bedrock_embedding_model_id=settings.bedrock_embedding_model_id,
    )


def get_feedback_provider() -> FeedbackProvider:
    settings = get_settings()
    return RoutedFeedbackProvider(
        provider_mode=settings.provider_mode,
        region_name=settings.aws_region,
        model_id=settings.bedrock_model_id,
    )


def get_retrieval_service() -> RetrievalService:
    return RetrievalService(get_content_repository(), get_vector_store())


def get_ingestion_service() -> IngestionService:
    return IngestionService(get_content_repository(), get_retrieval_service(), get_file_storage())


def get_evaluation_service() -> EvaluationService:
    return EvaluationService(get_retrieval_service(), get_feedback_provider())


def get_interview_service() -> InterviewService:
    return InterviewService(
        auth_service=get_auth_service(),
        content_repository=get_content_repository(),
        interview_repository=get_interview_repository(),
        evaluation_service=get_evaluation_service(),
        retrieval_service=get_retrieval_service(),
    )


def get_reporting_service() -> ReportingService:
    return ReportingService(
        content_repository=get_content_repository(),
        interview_repository=get_interview_repository(),
    )


__all__ = [
    "AuthService",
    "ContentRepository",
    "EvaluationService",
    "FeedbackProvider",
    "IngestionService",
    "InterviewRepository",
    "InterviewService",
    "LocalFileStorage",
    "ReportingService",
    "RetrievalService",
    "Settings",
    "ChromaContextVectorStore",
    "UserRepository",
    "get_auth_service",
    "get_content_repository",
    "get_evaluation_service",
    "get_feedback_provider",
    "get_file_storage",
    "get_ingestion_service",
    "get_interview_repository",
    "get_interview_service",
    "get_reporting_service",
    "get_retrieval_service",
    "get_settings",
    "get_user_repository",
    "get_vector_store",
]
