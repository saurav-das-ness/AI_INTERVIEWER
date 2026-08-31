"""Interview orchestration service for candidate sessions and follow-up flows."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.domain.user import UserRole
from app.models.schemas.interview import (
    AnswerSubmissionResponse,
    CandidateEvaluationResponse,
    FollowupQuestionResponse,
    QuestionViewResponse,
    SessionQuestionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SubmitAnswerRequest,
    SubmitFollowupRequest,
)
from app.repositories.content_repository import SqliteContentRepository
from app.repositories.interview_repository import SqliteInterviewRepository
from app.services.auth.service import AuthService, AuthenticationError
from app.services.evaluation.service import EvaluationService
from app.services.retrieval.service import RetrievalService


class InterviewError(ValueError):
    """Raised when interview flow operations are invalid."""


MAX_QUESTIONS_PER_SESSION = 5


class InterviewService:
    """Orchestrates question progression, scoring, follow-ups, and session state."""

    def __init__(
        self,
        *,
        auth_service: AuthService,
        content_repository: SqliteContentRepository,
        interview_repository: SqliteInterviewRepository,
        evaluation_service: EvaluationService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._auth_service = auth_service
        self._content_repository = content_repository
        self._interview_repository = interview_repository
        self._evaluation_service = evaluation_service
        self._retrieval_service = retrieval_service

    def start_session(self, payload: SessionStartRequest) -> SessionStartResponse:
        topic = self._content_repository.get_topic_by_id(payload.topic_id)
        if topic is None or not topic.published:
            raise InterviewError("Topic is not available for interviews")

        candidate = self._find_user_by_id(payload.candidate_id)
        if candidate is None or candidate.role != UserRole.CANDIDATE:
            raise InterviewError("Candidate account not found")

        questions = self._content_repository.list_questions_by_topic(topic.id, published_only=True)[:MAX_QUESTIONS_PER_SESSION]
        if not questions:
            raise InterviewError("Topic has no published questions")

        session = self._interview_repository.create_session(topic.id, candidate.id)
        return SessionStartResponse(
            session_id=session.id,
            status=session.status,
            question=self._question_to_view(topic.id, questions[0]),
        )

    def list_sessions(self, candidate_id: str):
        return self._interview_repository.list_sessions(candidate_id)

    def get_current_question(self, session_id: str) -> SessionQuestionResponse:
        session = self._get_session_or_error(session_id)
        questions = self._content_repository.list_questions_by_topic(session.topic_id, published_only=True)[:MAX_QUESTIONS_PER_SESSION]
        question = questions[session.question_index] if session.question_index < len(questions) else None
        return SessionQuestionResponse(
            session_id=session.id,
            status=session.status,
            question=self._question_to_view(session.topic_id, question) if question else None,
        )

    def submit_answer(self, payload: SubmitAnswerRequest) -> AnswerSubmissionResponse:
        session = self._get_session_or_error(payload.session_id)
        questions = self._content_repository.list_questions_by_topic(session.topic_id, published_only=True)[:MAX_QUESTIONS_PER_SESSION]
        if session.question_index >= len(questions):
            raise InterviewError("Interview session is already complete")

        current_question = questions[session.question_index]
        if current_question.id != payload.question_id:
            raise InterviewError("Submitted question does not match the current session state")

        answer = self._interview_repository.create_answer(
            session_id=session.id,
            question_id=current_question.id,
            answer_text=payload.answer_text,
            answer_order=session.question_index + 1,
        )
        rubric = self._content_repository.list_rubric_criteria(current_question.id)
        weight_config = self._content_repository.get_weight_config(current_question.id)
        if weight_config is None:
            raise InterviewError("Question is missing weight configuration")

        evaluation_result = self._evaluation_service.evaluate_answer(
            session_id=session.id,
            answer_id=answer.id,
            topic_id=session.topic_id,
            question=current_question,
            rubric_criteria=rubric,
            weight_config=weight_config,
            answer_text=payload.answer_text,
            final_version=True,
        )
        stored_initial = self._interview_repository.create_evaluation(evaluation_result.evaluation)
        self._store_audit_events(stored_initial)

        if evaluation_result.followup_required and evaluation_result.followup_prompt is not None:
            followup_count = len(self._interview_repository.list_followup_questions(answer.id)) + 1
            followup = self._interview_repository.create_followup_question(
                answer_id=answer.id,
                sequence_no=followup_count,
                prompt_text=evaluation_result.followup_prompt,
                purpose=evaluation_result.followup_purpose or "Probe missing details",
                linked_criteria=evaluation_result.linked_criteria,
            )
            self._interview_repository.update_session(
                session.id,
                status="awaiting_followup",
                question_index=session.question_index,
                average_score=session.average_score,
                completed_at=session.completed_at,
            )
            return AnswerSubmissionResponse(
                session_id=session.id,
                status="awaiting_followup",
                answer_id=answer.id,
                submitted_at=answer.submitted_at,
                evaluation=None,
                followup=FollowupQuestionResponse(
                    followup_id=followup.id,
                    prompt=followup.prompt_text,
                    purpose=followup.purpose,
                    followup_sequence=followup.sequence_no,
                    max_followups=weight_config.max_followups,
                ),
                next_question=None,
                interview_complete=False,
            )

        next_question = self._advance_session_after_final_evaluation(session, questions, stored_initial)
        return AnswerSubmissionResponse(
            session_id=session.id,
            status="completed" if next_question is None else "in_progress",
            answer_id=answer.id,
            submitted_at=answer.submitted_at,
            evaluation=CandidateEvaluationResponse(**self._evaluation_service.to_candidate_projection(stored_initial)),
            followup=None,
            next_question=self._question_to_view(session.topic_id, next_question) if next_question else None,
            interview_complete=next_question is None,
        )

    def submit_followup(self, payload: SubmitFollowupRequest) -> AnswerSubmissionResponse:
        session = self._get_session_or_error(payload.session_id)
        followup = self._interview_repository.get_followup_question(payload.followup_id)
        if followup is None:
            raise InterviewError("Follow-up question not found")

        answer = self._interview_repository.get_answer(followup.answer_id)
        if answer is None:
            raise InterviewError("Primary answer not found for follow-up")
        question = self._content_repository.get_question_by_id(answer.question_id)
        if question is None:
            raise InterviewError("Question not found for follow-up")

        followup_answer = self._interview_repository.create_followup_answer(followup.id, payload.answer_text)
        prior_evaluations = self._interview_repository.list_evaluations_for_answer(answer.id)
        prior_evaluation_id = prior_evaluations[-1].id if prior_evaluations else None
        rubric = self._content_repository.list_rubric_criteria(question.id)
        weight_config = self._content_repository.get_weight_config(question.id)
        if weight_config is None:
            raise InterviewError("Question is missing weight configuration")

        all_followup_answers = self._interview_repository.list_followup_answers_for_answer(answer.id)
        computation = self._evaluation_service.evaluate_answer(
            session_id=session.id,
            answer_id=answer.id,
            topic_id=session.topic_id,
            question=question,
            rubric_criteria=rubric,
            weight_config=weight_config,
            answer_text=answer.answer_text,
            followup_texts=[item.answer_text for item in all_followup_answers],
            followup_answer_id=followup_answer.id,
            replaces_evaluation_id=prior_evaluation_id,
            final_version=True,
        )
        stored_final = self._interview_repository.create_evaluation(computation.evaluation)
        self._store_audit_events(stored_final)

        # Chain another follow-up only when confidence is still mid; low or high both finalize.
        rescore_band = computation.evaluation.confidence_band
        if computation.followup_required and computation.followup_prompt is not None and rescore_band == "mid":
            next_seq = len(all_followup_answers) + 1
            next_followup = self._interview_repository.create_followup_question(
                answer_id=answer.id,
                sequence_no=next_seq,
                prompt_text=computation.followup_prompt,
                purpose=computation.followup_purpose or "Probe missing details",
                linked_criteria=computation.linked_criteria,
            )
            self._interview_repository.update_session(
                session.id,
                status="awaiting_followup",
                question_index=session.question_index,
                average_score=session.average_score,
                completed_at=session.completed_at,
            )
            return AnswerSubmissionResponse(
                session_id=session.id,
                status="awaiting_followup",
                answer_id=answer.id,
                submitted_at=followup_answer.submitted_at,
                evaluation=CandidateEvaluationResponse(**self._evaluation_service.to_candidate_projection(stored_final)),
                followup=FollowupQuestionResponse(
                    followup_id=next_followup.id,
                    prompt=next_followup.prompt_text,
                    purpose=next_followup.purpose,
                    followup_sequence=next_seq,
                    max_followups=weight_config.max_followups,
                ),
                next_question=None,
                interview_complete=False,
            )

        questions = self._content_repository.list_questions_by_topic(session.topic_id, published_only=True)[:MAX_QUESTIONS_PER_SESSION]
        next_question = self._advance_session_after_final_evaluation(session, questions, stored_final)
        return AnswerSubmissionResponse(
            session_id=session.id,
            status="completed" if next_question is None else "in_progress",
            answer_id=answer.id,
            submitted_at=followup_answer.submitted_at,
            evaluation=CandidateEvaluationResponse(**self._evaluation_service.to_candidate_projection(stored_final)),
            followup=None,
            next_question=self._question_to_view(session.topic_id, next_question) if next_question else None,
            interview_complete=next_question is None,
        )

    def _advance_session_after_final_evaluation(self, session, questions, evaluation):
        next_index = session.question_index + 1
        final_evaluations = self._interview_repository.list_final_evaluations_for_session(session.id)
        average = round(sum(item.percentage for item in final_evaluations) / len(final_evaluations), 2) if final_evaluations else evaluation.percentage
        if next_index >= len(questions):
            self._interview_repository.update_session(
                session.id,
                status="completed",
                question_index=next_index,
                average_score=average,
                completed_at=datetime.now(timezone.utc),
            )
            return None

        self._interview_repository.update_session(
            session.id,
            status="in_progress",
            question_index=next_index,
            average_score=average,
            completed_at=None,
        )
        return questions[next_index]

    def _store_audit_events(self, evaluation) -> None:
        for evidence in evaluation.evidence_references:
            self._interview_repository.create_audit_event(
                evaluation_result_id=evaluation.id,
                context_id=evidence.get("context_id"),
                event_type="evidence_reference",
                model_provider=str(evaluation.model_metadata.get("provider", "local-fallback")),
                model_name=str(evaluation.model_metadata.get("model_name", "heuristic-evaluator")),
                evidence_ref=str(evidence.get("context_code", "")),
            )

    def _find_user_by_id(self, user_id: str):
        repository = self._auth_service._user_repository
        if hasattr(repository, "get_by_id"):
            return repository.get_by_id(user_id)
        return None

    def _get_session_or_error(self, session_id: str):
        session = self._interview_repository.get_session(session_id)
        if session is None:
            raise InterviewError("Session not found")
        return session

    def _question_to_view(self, topic_id: str, question) -> QuestionViewResponse | None:
        if question is None:
            return None
        grounding = self._retrieval_service.retrieve(
            topic_id=topic_id,
            question_id=question.id,
            query_text=question.question_text,
            limit=3,
            allowed_source_types={"pdf", "manual", "text", "question"},
        )
        grounding_chunks = [
            {
                "source_label": str(item.get("source_label") or item.get("context_code") or "Reference"),
                "excerpt": str(item.get("excerpt", ""))[:300],
                "relevance_score": float(item.get("relevance_score", 0.0)),
            }
            for item in grounding
            if item.get("excerpt")
        ]
        return QuestionViewResponse(
            id=question.id,
            question_code=question.question_code,
            question_text=question.question_text,
            question_type=question.question_type,
            difficulty=question.difficulty,
            prompt_notes=question.prompt_notes,
            time_limit_seconds=question.time_limit_seconds,
            grounding_chunks=grounding_chunks,
        )
