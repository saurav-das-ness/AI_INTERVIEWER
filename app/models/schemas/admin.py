"""Administrative request and response schemas for content management."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ImportMessage(BaseModel):
    """Validation message returned during import preview."""

    severity: Literal["error", "warning"]
    field_name: str | None = None
    row_number: int | None = None
    message: str


class TopicImportModel(BaseModel):
    """JSON topic import payload."""

    topic_code: str
    topic_name: str
    description: str = ""
    published: bool = False


class RubricCriterionImportModel(BaseModel):
    """JSON rubric criterion import payload."""

    criterion_code: str
    criterion_name: str
    criterion_description: str
    weight: float
    min_score: float = 0
    max_score: float = 5
    evidence_required: bool = True


class QuestionImportModel(BaseModel):
    """JSON question import payload."""

    question_code: str
    question_text: str
    question_type: str
    difficulty: str
    expected_answer_summary: str
    followup_enabled: bool
    max_followups: int = Field(ge=0, le=3)
    confidence_thresholds: dict[str, float]
    tags: list[str] = Field(default_factory=list)
    language: str | None = None
    context_codes: list[str] = Field(default_factory=list)
    rubric: list[RubricCriterionImportModel]
    published: bool | None = None
    question_prompt_notes: str | None = None
    time_limit_seconds: int | None = None
    source_reference: str | None = None


class ContextImportModel(BaseModel):
    """JSON context import payload."""

    context_code: str
    scope_type: Literal["topic", "question"]
    scope_code: str
    context_title: str
    context_text: str
    source_type: str
    published: bool | None = None
    page_reference: str | None = None
    section_reference: str | None = None
    priority: int = 0
    notes: str | None = None


class TopicPackageImportModel(BaseModel):
    """JSON bulk import root payload."""

    topic: TopicImportModel
    questions: list[QuestionImportModel]
    contexts: list[ContextImportModel] = Field(default_factory=list)


class JsonImportRequest(BaseModel):
    """Request payload for JSON package import."""

    created_by: str
    package: TopicPackageImportModel


class CsvImportRequest(BaseModel):
    """Request payload for CSV-based question-bank import."""

    created_by: str
    csv_text: str


class ImportPreviewResponse(BaseModel):
    """Preview result returned before persistence."""

    valid: bool
    messages: list[ImportMessage] = Field(default_factory=list)
    topic_count: int = 0
    question_count: int = 0
    context_count: int = 0
    rubric_count: int = 0


class ImportApplyResponse(BaseModel):
    """Persistence summary returned after import success."""

    topic_id: str
    topic_code: str
    topic_name: str
    question_count: int
    context_count: int
    rubric_count: int
    published: bool


class PublishTopicRequest(BaseModel):
    """Payload for publish and unpublish operations."""

    published: bool


class TopicSummaryResponse(BaseModel):
    """Admin-facing topic summary."""

    id: str
    topic_code: str
    topic_name: str
    description: str
    published: bool
    question_count: int = 0
