"""Content-related domain entities for interview topics and rubrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Topic:
    """Interview topic group managed by admins."""

    id: str
    topic_code: str
    topic_name: str
    description: str
    created_by: str
    published: bool
    created_at: datetime
    question_count: int = 0


@dataclass(slots=True)
class Question:
    """Primary interview question stored under a topic."""

    id: str
    topic_id: str
    question_code: str
    question_text: str
    question_type: str
    difficulty: str
    expected_answer_summary: str
    followup_enabled: bool
    published: bool
    prompt_notes: str | None
    time_limit_seconds: int | None
    tags: list[str] = field(default_factory=list)
    language: str | None = None
    source_reference: str | None = None


@dataclass(slots=True)
class QuestionContext:
    """Approved context material linked to a topic or a specific question."""

    id: str
    topic_id: str
    question_id: str | None
    context_code: str
    source_type: str
    context_title: str
    context_text: str
    storage_ref: str | None
    page_reference: str | None
    section_reference: str | None
    priority: int
    published: bool
    created_at: datetime


@dataclass(slots=True)
class RubricCriterion:
    """Weighted scoring criterion used during answer evaluation."""

    id: str
    question_id: str
    criterion_code: str
    criterion_name: str
    criterion_description: str
    weight: float
    min_score: float
    max_score: float
    evidence_required: bool


@dataclass(slots=True)
class WeightConfig:
    """Follow-up thresholds and scoring controls for a question."""

    id: str
    question_id: str
    confidence_low: float
    confidence_mid_start: float
    confidence_mid_end: float
    confidence_high: float
    max_followups: int
