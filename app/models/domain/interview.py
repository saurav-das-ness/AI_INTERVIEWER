"""Interview session, answer, evaluation, and audit domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class InterviewSession:
    """Candidate interview session state."""

    id: str
    topic_id: str
    candidate_id: str
    status: str
    question_index: int
    started_at: datetime
    completed_at: datetime | None
    average_score: float | None


@dataclass(slots=True)
class CandidateAnswer:
    """Primary answer submitted by a candidate."""

    id: str
    session_id: str
    question_id: str
    answer_text: str
    answer_order: int
    submitted_at: datetime


@dataclass(slots=True)
class FollowUpQuestion:
    """Follow-up prompt generated for a primary answer."""

    id: str
    answer_id: str
    sequence_no: int
    prompt_text: str
    purpose: str
    linked_criteria: list[str] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass(slots=True)
class FollowUpAnswer:
    """Candidate response to a follow-up question."""

    id: str
    followup_question_id: str
    answer_text: str
    submitted_at: datetime


@dataclass(slots=True)
class EvaluationResult:
    """Structured evaluation output for a candidate answer."""

    id: str
    candidate_answer_id: str
    followup_answer_id: str | None
    replaces_evaluation_id: str | None
    raw_score: float
    max_score: float
    normalized_score: float
    percentage: float
    confidence_score: float
    confidence_band: str
    finalize_decision: str
    criteria_results: list[dict[str, object]] = field(default_factory=list)
    feedback: dict[str, object] = field(default_factory=dict)
    evidence_references: list[dict[str, object]] = field(default_factory=list)
    model_metadata: dict[str, object] = field(default_factory=dict)
    audit_payload: dict[str, object] = field(default_factory=dict)
    final_version: bool = True
    created_at: datetime | None = None


@dataclass(slots=True)
class AuditEvent:
    """Traceability event linked to an evaluation."""

    id: str
    evaluation_result_id: str
    context_id: str | None
    event_type: str
    model_provider: str
    model_name: str
    evidence_ref: str
    created_at: datetime
