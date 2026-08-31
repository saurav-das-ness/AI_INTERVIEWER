"""Application settings for the backend slice."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the current MVP backend slice."""

    app_name: str = "AI Interview Tool"
    sqlite_db_path: str = "storage/app.db"
    chroma_persist_dir: str = "storage/chroma"
    chroma_collection_name: str = "ai_interview_context"
    uploads_dir: str = "storage/uploads"
    aws_region: str | None = None
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    provider_mode: str = "bedrock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment with safe defaults for local development."""

    sqlite_db_path = os.getenv("AI_INTERVIEW_SQLITE_DB", "storage/app.db")
    chroma_persist_dir = os.getenv("AI_INTERVIEW_CHROMA_DIR", "storage/chroma")
    uploads_dir = os.getenv("AI_INTERVIEW_UPLOADS_DIR", "storage/uploads")
    Path(sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(uploads_dir).mkdir(parents=True, exist_ok=True)
    return Settings(
        sqlite_db_path=sqlite_db_path,
        chroma_persist_dir=chroma_persist_dir,
        chroma_collection_name=os.getenv("AI_INTERVIEW_CHROMA_COLLECTION", "ai_interview_context"),
        uploads_dir=uploads_dir,
        aws_region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
        bedrock_model_id=os.getenv("AI_INTERVIEW_BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
        bedrock_embedding_model_id=os.getenv("AI_INTERVIEW_BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        provider_mode=os.getenv("AI_INTERVIEW_PROVIDER_MODE", "bedrock"),
    )
