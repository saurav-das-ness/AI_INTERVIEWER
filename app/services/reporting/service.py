"""Reporting service for session summaries and admin reviews."""

from __future__ import annotations

from collections import Counter

from app.models.schemas.reporting import AdminEvaluationReviewResponse, SessionAnswerSummaryResponse, SessionSummaryResponse
from app.repositories.content_repository import SqliteContentRepository
from app.repositories.interview_repository import SqliteInterviewRepository
from app.services.interview.service import InterviewError


class ReportingService:
    """Builds candidate-safe summaries and detailed admin review payloads."""

    def __init__(self, *, content_repository: SqliteContentRepository, interview_repository: SqliteInterviewRepository) -> None:
        self._content_repository = content_repository
        self._interview_repository = interview_repository

    def get_session_summary(self, session_id: str) -> SessionSummaryResponse:
        session = self._interview_repository.get_session(session_id)
        if session is None:
            raise InterviewError("Session not found")

        answers = self._interview_repository.list_answers(session.id)
        evaluations = self._interview_repository.list_final_evaluations_for_session(session.id)
        answer_summaries: list[SessionAnswerSummaryResponse] = []
        strengths_counter: Counter[str] = Counter()
        gaps_counter: Counter[str] = Counter()

        for answer, evaluation in zip(answers, evaluations):
            question = self._content_repository.get_question_by_id(answer.question_id)
            followups_used = len(self._interview_repository.list_followup_questions(answer.id))
            answer_summaries.append(
                SessionAnswerSummaryResponse(
                    question_code=question.question_code if question else answer.question_id,
                    score_percentage=evaluation.percentage,
                    confidence_band=evaluation.confidence_band,
                    followups_used=followups_used,
                )
            )
            strengths_counter.update(evaluation.feedback.get("strengths", []))
            gaps_counter.update(evaluation.feedback.get("gaps", []))

        average = round(sum(item.score_percentage for item in answer_summaries) / len(answer_summaries), 2) if answer_summaries else 0.0
        return SessionSummaryResponse(
            session_id=session.id,
            candidate_id=session.candidate_id,
            topic_id=session.topic_id,
            started_at_utc=session.started_at,
            completed_at_utc=session.completed_at,
            question_count=len(answer_summaries),
            average_score_percentage=average,
            overall_strengths=[item for item, _ in strengths_counter.most_common(3)],
            overall_gaps=[item for item, _ in gaps_counter.most_common(3)],
            answers=answer_summaries,
        )

    def list_session_summaries(self, candidate_id: str | None = None) -> list[SessionSummaryResponse]:
        sessions = self._interview_repository.list_sessions(candidate_id)
        return [self.get_session_summary(session.id) for session in sessions if session.status == "completed"]

    def get_admin_session_review(self, session_id: str) -> AdminEvaluationReviewResponse:
        session = self._interview_repository.get_session(session_id)
        if session is None:
            raise InterviewError("Session not found")

        answers = self._interview_repository.list_answers(session.id)
        evaluations_payload: list[dict[str, object]] = []
        for answer in answers:
            question = self._content_repository.get_question_by_id(answer.question_id)
            evaluations = self._interview_repository.list_evaluations_for_answer(answer.id)
            for evaluation in evaluations:
                evaluations_payload.append(
                    {
                        "question_code": question.question_code if question else answer.question_id,
                        "question_text": question.question_text if question else "",
                        "answer_id": answer.id,
                        "evaluation_id": evaluation.id,
                        "final_version": evaluation.final_version,
                        "score_percentage": evaluation.percentage,
                        "confidence_band": evaluation.confidence_band,
                        "criteria_results": evaluation.criteria_results,
                        "feedback": evaluation.feedback,
                        "evidence_references": evaluation.evidence_references,
                        "thresholds_applied": evaluation.audit_payload.get("thresholds_applied", {}),
                        "model_metadata": evaluation.model_metadata,
                        "followups_used": len(self._interview_repository.list_followup_questions(answer.id)),
                    }
                )

        summary = self.get_session_summary(session.id)
        return AdminEvaluationReviewResponse(
            session_id=session.id,
            candidate_id=session.candidate_id,
            topic_id=session.topic_id,
            status=session.status,
            question_count=summary.question_count,
            average_score_percentage=summary.average_score_percentage,
            evaluations=evaluations_payload,
        )

