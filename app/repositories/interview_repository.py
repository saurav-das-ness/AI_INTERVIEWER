"""SQLite-backed repository for interview sessions, answers, evaluations, and audit data."""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol

from app.db.sqlite import connect, initialize_schema
from app.models.domain.interview import AuditEvent, CandidateAnswer, EvaluationResult, FollowUpAnswer, FollowUpQuestion, InterviewSession


class InterviewRepository(Protocol):
    """Persistence contract for interview runtime data."""


class SqliteInterviewRepository:
    """SQLite repository for runtime interview state and evaluations."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        with connect(self._db_path) as connection:
            initialize_schema(connection)

    def create_session(self, topic_id: str, candidate_id: str) -> InterviewSession:
        session = InterviewSession(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            candidate_id=candidate_id,
            status="in_progress",
            question_index=0,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            average_score=None,
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO interview_sessions (id, topic_id, candidate_id, status, question_index, started_at, completed_at, average_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.topic_id,
                    session.candidate_id,
                    session.status,
                    session.question_index,
                    session.started_at.isoformat(),
                    None,
                    None,
                ),
            )
            connection.commit()
        return session

    def get_session(self, session_id: str) -> InterviewSession | None:
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_session(row) if row else None

    def update_session(
        self,
        session_id: str,
        *,
        status: str,
        question_index: int,
        average_score: float | None,
        completed_at: datetime | None,
    ) -> InterviewSession:
        with connect(self._db_path) as connection:
            connection.execute(
                """
                UPDATE interview_sessions
                SET status = ?, question_index = ?, average_score = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    question_index,
                    average_score,
                    completed_at.isoformat() if completed_at else None,
                    session_id,
                ),
            )
            connection.commit()
        return self.get_session(session_id)

    def create_answer(self, session_id: str, question_id: str, answer_text: str, answer_order: int) -> CandidateAnswer:
        answer = CandidateAnswer(
            id=str(uuid.uuid4()),
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text,
            answer_order=answer_order,
            submitted_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO candidate_answers (id, session_id, question_id, answer_text, answer_order, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    answer.id,
                    answer.session_id,
                    answer.question_id,
                    answer.answer_text,
                    answer.answer_order,
                    answer.submitted_at.isoformat(),
                ),
            )
            connection.commit()
        return answer

    def get_answer(self, answer_id: str) -> CandidateAnswer | None:
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM candidate_answers WHERE id = ?", (answer_id,)).fetchone()
        return self._row_to_answer(row) if row else None

    def list_answers(self, session_id: str) -> list[CandidateAnswer]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM candidate_answers WHERE session_id = ? ORDER BY answer_order",
                (session_id,),
            ).fetchall()
        return [self._row_to_answer(row) for row in rows]

    def create_followup_question(self, answer_id: str, sequence_no: int, prompt_text: str, purpose: str, linked_criteria: list[str]) -> FollowUpQuestion:
        followup = FollowUpQuestion(
            id=str(uuid.uuid4()),
            answer_id=answer_id,
            sequence_no=sequence_no,
            prompt_text=prompt_text,
            purpose=purpose,
            linked_criteria=linked_criteria,
            created_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO followup_questions (id, answer_id, sequence_no, prompt_text, purpose, linked_criteria_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    followup.id,
                    followup.answer_id,
                    followup.sequence_no,
                    followup.prompt_text,
                    followup.purpose,
                    json.dumps(followup.linked_criteria),
                    followup.created_at.isoformat(),
                ),
            )
            connection.commit()
        return followup

    def get_followup_question(self, followup_id: str) -> FollowUpQuestion | None:
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM followup_questions WHERE id = ?", (followup_id,)).fetchone()
        return self._row_to_followup_question(row) if row else None

    def list_followup_questions(self, answer_id: str) -> list[FollowUpQuestion]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM followup_questions WHERE answer_id = ? ORDER BY sequence_no",
                (answer_id,),
            ).fetchall()
        return [self._row_to_followup_question(row) for row in rows]

    def create_followup_answer(self, followup_question_id: str, answer_text: str) -> FollowUpAnswer:
        followup_answer = FollowUpAnswer(
            id=str(uuid.uuid4()),
            followup_question_id=followup_question_id,
            answer_text=answer_text,
            submitted_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO followup_answers (id, followup_question_id, answer_text, submitted_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    followup_answer.id,
                    followup_answer.followup_question_id,
                    followup_answer.answer_text,
                    followup_answer.submitted_at.isoformat(),
                ),
            )
            connection.commit()
        return followup_answer

    def list_followup_answers_for_answer(self, answer_id: str) -> list[FollowUpAnswer]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT fa.*
                FROM followup_answers fa
                JOIN followup_questions fq ON fq.id = fa.followup_question_id
                WHERE fq.answer_id = ?
                ORDER BY fq.sequence_no
                """,
                (answer_id,),
            ).fetchall()
        return [self._row_to_followup_answer(row) for row in rows]

    def create_evaluation(self, evaluation: EvaluationResult) -> EvaluationResult:
        stored = replace(
            evaluation,
            id=evaluation.id or str(uuid.uuid4()),
            created_at=evaluation.created_at or datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO evaluation_results (
                    id, candidate_answer_id, followup_answer_id, replaces_evaluation_id,
                    raw_score, max_score, normalized_score, percentage, confidence_score,
                    confidence_band, finalize_decision, criteria_results_json, feedback_json,
                    evidence_references_json, model_metadata_json, audit_payload_json,
                    final_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.id,
                    stored.candidate_answer_id,
                    stored.followup_answer_id,
                    stored.replaces_evaluation_id,
                    stored.raw_score,
                    stored.max_score,
                    stored.normalized_score,
                    stored.percentage,
                    stored.confidence_score,
                    stored.confidence_band,
                    stored.finalize_decision,
                    json.dumps(stored.criteria_results),
                    json.dumps(stored.feedback),
                    json.dumps(stored.evidence_references),
                    json.dumps(stored.model_metadata),
                    json.dumps(stored.audit_payload),
                    int(stored.final_version),
                    stored.created_at.isoformat(),
                ),
            )
            connection.commit()
        return stored

    def list_evaluations_for_answer(self, answer_id: str) -> list[EvaluationResult]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM evaluation_results WHERE candidate_answer_id = ? ORDER BY created_at",
                (answer_id,),
            ).fetchall()
        return [self._row_to_evaluation(row) for row in rows]

    def list_final_evaluations_for_session(self, session_id: str) -> list[EvaluationResult]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT er.*
                FROM evaluation_results er
                JOIN candidate_answers ca ON ca.id = er.candidate_answer_id
                WHERE ca.session_id = ? AND er.final_version = 1
                ORDER BY ca.answer_order
                """,
                (session_id,),
            ).fetchall()
        return [self._row_to_evaluation(row) for row in rows]

    def list_sessions(self, candidate_id: str | None = None) -> list[InterviewSession]:
        with connect(self._db_path) as connection:
            if candidate_id:
                rows = connection.execute(
                    "SELECT * FROM interview_sessions WHERE candidate_id = ? ORDER BY started_at DESC",
                    (candidate_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM interview_sessions ORDER BY started_at DESC"
                ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def create_audit_event(self, evaluation_result_id: str, context_id: str | None, event_type: str, model_provider: str, model_name: str, evidence_ref: str) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid.uuid4()),
            evaluation_result_id=evaluation_result_id,
            context_id=context_id,
            event_type=event_type,
            model_provider=model_provider,
            model_name=model_name,
            evidence_ref=evidence_ref,
            created_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, evaluation_result_id, context_id, event_type, model_provider,
                    model_name, evidence_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.evaluation_result_id,
                    event.context_id,
                    event.event_type,
                    event.model_provider,
                    event.model_name,
                    event.evidence_ref,
                    event.created_at.isoformat(),
                ),
            )
            connection.commit()
        return event

    def list_audit_events_for_evaluation(self, evaluation_result_id: str) -> list[AuditEvent]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events WHERE evaluation_result_id = ? ORDER BY created_at",
                (evaluation_result_id,),
            ).fetchall()
        return [self._row_to_audit_event(row) for row in rows]

    @staticmethod
    def _row_to_session(row: object) -> InterviewSession:
        return InterviewSession(
            id=row["id"],
            topic_id=row["topic_id"],
            candidate_id=row["candidate_id"],
            status=row["status"],
            question_index=int(row["question_index"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            average_score=float(row["average_score"]) if row["average_score"] is not None else None,
        )

    @staticmethod
    def _row_to_answer(row: object) -> CandidateAnswer:
        return CandidateAnswer(
            id=row["id"],
            session_id=row["session_id"],
            question_id=row["question_id"],
            answer_text=row["answer_text"],
            answer_order=int(row["answer_order"]),
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
        )

    @staticmethod
    def _row_to_followup_question(row: object) -> FollowUpQuestion:
        return FollowUpQuestion(
            id=row["id"],
            answer_id=row["answer_id"],
            sequence_no=int(row["sequence_no"]),
            prompt_text=row["prompt_text"],
            purpose=row["purpose"],
            linked_criteria=json.loads(row["linked_criteria_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_followup_answer(row: object) -> FollowUpAnswer:
        return FollowUpAnswer(
            id=row["id"],
            followup_question_id=row["followup_question_id"],
            answer_text=row["answer_text"],
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
        )

    @staticmethod
    def _row_to_evaluation(row: object) -> EvaluationResult:
        return EvaluationResult(
            id=row["id"],
            candidate_answer_id=row["candidate_answer_id"],
            followup_answer_id=row["followup_answer_id"],
            replaces_evaluation_id=row["replaces_evaluation_id"],
            raw_score=float(row["raw_score"]),
            max_score=float(row["max_score"]),
            normalized_score=float(row["normalized_score"]),
            percentage=float(row["percentage"]),
            confidence_score=float(row["confidence_score"]),
            confidence_band=row["confidence_band"],
            finalize_decision=row["finalize_decision"],
            criteria_results=json.loads(row["criteria_results_json"]),
            feedback=json.loads(row["feedback_json"]),
            evidence_references=json.loads(row["evidence_references_json"]),
            model_metadata=json.loads(row["model_metadata_json"]),
            audit_payload=json.loads(row["audit_payload_json"]),
            final_version=bool(row["final_version"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_audit_event(row: object) -> AuditEvent:
        return AuditEvent(
            id=row["id"],
            evaluation_result_id=row["evaluation_result_id"],
            context_id=row["context_id"],
            event_type=row["event_type"],
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            evidence_ref=row["evidence_ref"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
