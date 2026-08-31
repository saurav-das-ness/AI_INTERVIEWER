"""Schemas for candidate summaries and admin review outputs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionAnswerSummaryResponse(BaseModel):
    """Per-question summary within a completed session."""

    question_code: str
    score_percentage: float
    confidence_band: str
    followups_used: int


class SessionSummaryResponse(BaseModel):
    """Candidate-safe completed session summary."""

    session_id: str
    candidate_id: str
    topic_id: str
    started_at_utc: datetime
    completed_at_utc: datetime | None
    question_count: int
    average_score_percentage: float
    overall_strengths: list[str] = Field(default_factory=list)
    overall_gaps: list[str] = Field(default_factory=list)
    answers: list[SessionAnswerSummaryResponse] = Field(default_factory=list)


class AdminEvaluationReviewResponse(BaseModel):
    """Detailed admin review for a completed interview session."""

    session_id: str
    candidate_id: str
    topic_id: str
    status: str
    question_count: int
    average_score_percentage: float
    evaluations: list[dict[str, object]] = Field(default_factory=list)
