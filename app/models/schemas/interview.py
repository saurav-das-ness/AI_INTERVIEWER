"""Schemas for candidate interview flows and answer submission."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionViewResponse(BaseModel):
    """Candidate-facing question projection."""

    id: str
    question_code: str
    question_text: str
    question_type: str
    difficulty: str
    prompt_notes: str | None = None
    time_limit_seconds: int | None = None
    grounding_chunks: list[EvidenceChunkResponse] = Field(default_factory=list)


class EvidenceChunkResponse(BaseModel):
    """Candidate-visible excerpt from a retrieved reference chunk."""

    source_label: str
    excerpt: str
    relevance_score: float


class CandidateEvaluationResponse(BaseModel):
    """Safe answer feedback visible to the candidate."""

    evaluation_id: str
    score_percentage: float
    confidence_band: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    summary: str
    evidence_chunks: list[EvidenceChunkResponse] = Field(default_factory=list)


class FollowupQuestionResponse(BaseModel):
    """Follow-up prompt returned when confidence is mid-band."""

    followup_id: str
    prompt: str
    purpose: str
    followup_sequence: int
    max_followups: int


class SessionStartRequest(BaseModel):
    """Start an interview session for a topic and candidate."""

    candidate_id: str
    topic_id: str


class SessionStartResponse(BaseModel):
    """Result of creating a new interview session."""

    session_id: str
    status: str
    question: QuestionViewResponse | None = None


class SessionQuestionResponse(BaseModel):
    """Current question lookup result."""

    session_id: str
    status: str
    question: QuestionViewResponse | None = None


class SubmitAnswerRequest(BaseModel):
    """Primary answer submission payload."""

    session_id: str
    question_id: str
    answer_text: str = Field(min_length=1)


class SubmitFollowupRequest(BaseModel):
    """Follow-up answer submission payload."""

    session_id: str
    followup_id: str
    answer_text: str = Field(min_length=1)


class AnswerSubmissionResponse(BaseModel):
    """Result of a primary or follow-up answer submission."""

    session_id: str
    status: str
    answer_id: str
    submitted_at: datetime
    evaluation: CandidateEvaluationResponse | None = None
    followup: FollowupQuestionResponse | None = None
    next_question: QuestionViewResponse | None = None
    interview_complete: bool = False
