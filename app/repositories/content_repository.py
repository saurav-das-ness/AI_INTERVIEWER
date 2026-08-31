"""SQLite-backed repository for topics, questions, contexts, and rubric data."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Protocol

from app.db.sqlite import connect, initialize_schema
from app.models.domain.content import Question, QuestionContext, RubricCriterion, Topic, WeightConfig


class ContentRepository(Protocol):
    """Persistence contract for content-management operations."""


class SqliteContentRepository:
    """SQLite repository for admin-managed content and configuration."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        with connect(self._db_path) as connection:
            initialize_schema(connection)

    def create_topic(self, topic_code: str, topic_name: str, description: str, created_by: str, published: bool) -> Topic:
        topic = Topic(
            id=str(uuid.uuid4()),
            topic_code=topic_code,
            topic_name=topic_name,
            description=description,
            created_by=created_by,
            published=published,
            created_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO topics (id, topic_code, topic_name, description, created_by, published, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    topic.id,
                    topic.topic_code,
                    topic.topic_name,
                    topic.description,
                    topic.created_by,
                    int(topic.published),
                    topic.created_at.isoformat(),
                ),
            )
            connection.commit()
        return topic

    def get_topic_by_code(self, topic_code: str) -> Topic | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT t.id, t.topic_code, t.topic_name, t.description, t.created_by, t.published, t.created_at,
                       COUNT(q.id) AS question_count
                FROM topics t
                LEFT JOIN questions q ON q.topic_id = t.id
                WHERE t.topic_code = ?
                GROUP BY t.id
                """,
                (topic_code,),
            ).fetchone()
        return self._row_to_topic(row) if row else None

    def get_topic_by_id(self, topic_id: str) -> Topic | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT t.id, t.topic_code, t.topic_name, t.description, t.created_by, t.published, t.created_at,
                       COUNT(q.id) AS question_count
                FROM topics t
                LEFT JOIN questions q ON q.topic_id = t.id
                WHERE t.id = ?
                GROUP BY t.id
                """,
                (topic_id,),
            ).fetchone()
        return self._row_to_topic(row) if row else None

    def list_topics(self, include_unpublished: bool = False) -> list[Topic]:
        query = """
            SELECT t.id, t.topic_code, t.topic_name, t.description, t.created_by, t.published, t.created_at,
                   COUNT(q.id) AS question_count
            FROM topics t
            LEFT JOIN questions q ON q.topic_id = t.id
        """
        params: tuple[object, ...] = ()
        if not include_unpublished:
            query += " WHERE t.published = 1"
        query += " GROUP BY t.id ORDER BY t.topic_name"
        with connect(self._db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_topic(row) for row in rows]

    def set_topic_publication(self, topic_id: str, published: bool) -> Topic | None:
        with connect(self._db_path) as connection:
            connection.execute("UPDATE topics SET published = ? WHERE id = ?", (int(published), topic_id))
            connection.execute("UPDATE questions SET published = ? WHERE topic_id = ?", (int(published), topic_id))
            connection.execute("UPDATE question_contexts SET published = ? WHERE topic_id = ?", (int(published), topic_id))
            connection.commit()
        return self.get_topic_by_id(topic_id)

    def create_question(
        self,
        topic_id: str,
        question_code: str,
        question_text: str,
        question_type: str,
        difficulty: str,
        expected_answer_summary: str,
        followup_enabled: bool,
        published: bool,
        prompt_notes: str | None,
        time_limit_seconds: int | None,
        tags: list[str],
        language: str | None,
        source_reference: str | None,
    ) -> Question:
        question = Question(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            question_code=question_code,
            question_text=question_text,
            question_type=question_type,
            difficulty=difficulty,
            expected_answer_summary=expected_answer_summary,
            followup_enabled=followup_enabled,
            published=published,
            prompt_notes=prompt_notes,
            time_limit_seconds=time_limit_seconds,
            tags=tags,
            language=language,
            source_reference=source_reference,
        )
        try:
            with connect(self._db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO questions (
                        id, topic_id, question_code, question_text, question_type, difficulty,
                        expected_answer_summary, followup_enabled, published, prompt_notes,
                        time_limit_seconds, tags_json, language, source_reference
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question.id,
                        question.topic_id,
                        question.question_code,
                        question.question_text,
                        question.question_type,
                        question.difficulty,
                        question.expected_answer_summary,
                        int(question.followup_enabled),
                        int(question.published),
                        question.prompt_notes,
                        question.time_limit_seconds,
                        json.dumps(question.tags),
                        question.language,
                        question.source_reference,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            if "questions.question_code" in str(exc):
                raise ValueError(
                    f"Question code '{question.question_code}' already exists. "
                    "Use unique question codes or edit existing questions instead."
                ) from exc
            raise
        return question

    def get_question_by_id(self, question_id: str) -> Question | None:
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        return self._row_to_question(row) if row else None

    def get_question_by_code(self, question_code: str) -> Question | None:
        with connect(self._db_path) as connection:
            row = connection.execute("SELECT * FROM questions WHERE question_code = ?", (question_code,)).fetchone()
        return self._row_to_question(row) if row else None

    def list_questions_by_topic(self, topic_id: str, published_only: bool = False) -> list[Question]:
        query = "SELECT * FROM questions WHERE topic_id = ?"
        params: list[object] = [topic_id]
        if published_only:
            query += " AND published = 1"
        query += " ORDER BY question_code"
        with connect(self._db_path) as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_question(row) for row in rows]

    def create_context(
        self,
        topic_id: str,
        question_id: str | None,
        context_code: str,
        source_type: str,
        context_title: str,
        context_text: str,
        storage_ref: str | None,
        page_reference: str | None,
        section_reference: str | None,
        priority: int,
        published: bool,
    ) -> QuestionContext:
        context = QuestionContext(
            id=str(uuid.uuid4()),
            topic_id=topic_id,
            question_id=question_id,
            context_code=context_code,
            source_type=source_type,
            context_title=context_title,
            context_text=context_text,
            storage_ref=storage_ref,
            page_reference=page_reference,
            section_reference=section_reference,
            priority=priority,
            published=published,
            created_at=datetime.now(timezone.utc),
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO question_contexts (
                    id, topic_id, question_id, context_code, source_type, context_title,
                    context_text, storage_ref, page_reference, section_reference,
                    priority, published, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    context.id,
                    context.topic_id,
                    context.question_id,
                    context.context_code,
                    context.source_type,
                    context.context_title,
                    context.context_text,
                    context.storage_ref,
                    context.page_reference,
                    context.section_reference,
                    context.priority,
                    int(context.published),
                    context.created_at.isoformat(),
                ),
            )
            connection.commit()
        return context

    def list_contexts(self, topic_id: str, question_id: str | None = None, published_only: bool = True) -> list[QuestionContext]:
        query = "SELECT * FROM question_contexts WHERE topic_id = ?"
        params: list[object] = [topic_id]
        if published_only:
            query += " AND published = 1"
        if question_id is not None:
            query += " AND (question_id = ? OR question_id IS NULL)"
            params.append(question_id)
        query += " ORDER BY priority DESC, context_code"
        with connect(self._db_path) as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_context(row) for row in rows]

    def create_rubric_criterion(
        self,
        question_id: str,
        criterion_code: str,
        criterion_name: str,
        criterion_description: str,
        weight: float,
        min_score: float,
        max_score: float,
        evidence_required: bool,
    ) -> RubricCriterion:
        criterion = RubricCriterion(
            id=str(uuid.uuid4()),
            question_id=question_id,
            criterion_code=criterion_code,
            criterion_name=criterion_name,
            criterion_description=criterion_description,
            weight=weight,
            min_score=min_score,
            max_score=max_score,
            evidence_required=evidence_required,
        )
        with connect(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO rubric_criteria (
                    id, question_id, criterion_code, criterion_name, criterion_description,
                    weight, min_score, max_score, evidence_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    criterion.id,
                    criterion.question_id,
                    criterion.criterion_code,
                    criterion.criterion_name,
                    criterion.criterion_description,
                    criterion.weight,
                    criterion.min_score,
                    criterion.max_score,
                    int(criterion.evidence_required),
                ),
            )
            connection.commit()
        return criterion

    def list_rubric_criteria(self, question_id: str) -> list[RubricCriterion]:
        with connect(self._db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM rubric_criteria WHERE question_id = ? ORDER BY criterion_code",
                (question_id,),
            ).fetchall()
        return [self._row_to_rubric(row) for row in rows]

    def upsert_weight_config(
        self,
        question_id: str,
        confidence_low: float,
        confidence_mid_start: float,
        confidence_mid_end: float,
        confidence_high: float,
        max_followups: int,
    ) -> WeightConfig:
        existing = self.get_weight_config(question_id)
        if existing is None:
            config = WeightConfig(
                id=str(uuid.uuid4()),
                question_id=question_id,
                confidence_low=confidence_low,
                confidence_mid_start=confidence_mid_start,
                confidence_mid_end=confidence_mid_end,
                confidence_high=confidence_high,
                max_followups=max_followups,
            )
            with connect(self._db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO weight_configs (
                        id, question_id, confidence_low, confidence_mid_start,
                        confidence_mid_end, confidence_high, max_followups
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        config.id,
                        config.question_id,
                        config.confidence_low,
                        config.confidence_mid_start,
                        config.confidence_mid_end,
                        config.confidence_high,
                        config.max_followups,
                    ),
                )
                connection.commit()
            return config

        with connect(self._db_path) as connection:
            connection.execute(
                """
                UPDATE weight_configs
                SET confidence_low = ?, confidence_mid_start = ?, confidence_mid_end = ?,
                    confidence_high = ?, max_followups = ?
                WHERE question_id = ?
                """,
                (confidence_low, confidence_mid_start, confidence_mid_end, confidence_high, max_followups, question_id),
            )
            connection.commit()
        return self.get_weight_config(question_id)

    def get_weight_config(self, question_id: str) -> WeightConfig | None:
        with connect(self._db_path) as connection:
            row = connection.execute(
                "SELECT * FROM weight_configs WHERE question_id = ?",
                (question_id,),
            ).fetchone()
        return self._row_to_weight_config(row) if row else None

    def update_rubric_criterion_weight(self, criterion_id: str, weight: float) -> RubricCriterion | None:
        with connect(self._db_path) as connection:
            connection.execute(
                "UPDATE rubric_criteria SET weight = ? WHERE id = ?",
                (weight, criterion_id),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM rubric_criteria WHERE id = ?",
                (criterion_id,),
            ).fetchone()
        return self._row_to_rubric(row) if row else None

    @staticmethod
    def _row_to_topic(row: object) -> Topic:
        return Topic(
            id=row["id"],
            topic_code=row["topic_code"],
            topic_name=row["topic_name"],
            description=row["description"],
            created_by=row["created_by"],
            published=bool(row["published"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            question_count=int(row["question_count"]),
        )

    @staticmethod
    def _row_to_question(row: object) -> Question:
        return Question(
            id=row["id"],
            topic_id=row["topic_id"],
            question_code=row["question_code"],
            question_text=row["question_text"],
            question_type=row["question_type"],
            difficulty=row["difficulty"],
            expected_answer_summary=row["expected_answer_summary"],
            followup_enabled=bool(row["followup_enabled"]),
            published=bool(row["published"]),
            prompt_notes=row["prompt_notes"],
            time_limit_seconds=row["time_limit_seconds"],
            tags=json.loads(row["tags_json"]),
            language=row["language"],
            source_reference=row["source_reference"],
        )

    @staticmethod
    def _row_to_context(row: object) -> QuestionContext:
        return QuestionContext(
            id=row["id"],
            topic_id=row["topic_id"],
            question_id=row["question_id"],
            context_code=row["context_code"],
            source_type=row["source_type"],
            context_title=row["context_title"],
            context_text=row["context_text"],
            storage_ref=row["storage_ref"],
            page_reference=row["page_reference"],
            section_reference=row["section_reference"],
            priority=int(row["priority"]),
            published=bool(row["published"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_rubric(row: object) -> RubricCriterion:
        return RubricCriterion(
            id=row["id"],
            question_id=row["question_id"],
            criterion_code=row["criterion_code"],
            criterion_name=row["criterion_name"],
            criterion_description=row["criterion_description"],
            weight=float(row["weight"]),
            min_score=float(row["min_score"]),
            max_score=float(row["max_score"]),
            evidence_required=bool(row["evidence_required"]),
        )

    @staticmethod
    def _row_to_weight_config(row: object) -> WeightConfig:
        return WeightConfig(
            id=row["id"],
            question_id=row["question_id"],
            confidence_low=float(row["confidence_low"]),
            confidence_mid_start=float(row["confidence_mid_start"]),
            confidence_mid_end=float(row["confidence_mid_end"]),
            confidence_high=float(row["confidence_high"]),
            max_followups=int(row["max_followups"]),
        )
