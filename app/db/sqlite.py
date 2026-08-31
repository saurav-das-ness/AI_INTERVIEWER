"""SQLite helpers for local transactional persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path


USER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

TOPIC_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    topic_code TEXT NOT NULL UNIQUE,
    topic_name TEXT NOT NULL,
    description TEXT NOT NULL,
    created_by TEXT NOT NULL,
    published INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
"""

QUESTION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    question_code TEXT NOT NULL UNIQUE,
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    expected_answer_summary TEXT NOT NULL,
    followup_enabled INTEGER NOT NULL,
    published INTEGER NOT NULL,
    prompt_notes TEXT,
    time_limit_seconds INTEGER,
    tags_json TEXT NOT NULL,
    language TEXT,
    source_reference TEXT,
    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
)
"""

QUESTION_CONTEXT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_contexts (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    question_id TEXT,
    context_code TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    context_title TEXT NOT NULL,
    context_text TEXT NOT NULL,
    storage_ref TEXT,
    page_reference TEXT,
    section_reference TEXT,
    priority INTEGER NOT NULL,
    published INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
)
"""

RUBRIC_CRITERION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rubric_criteria (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    criterion_code TEXT NOT NULL,
    criterion_name TEXT NOT NULL,
    criterion_description TEXT NOT NULL,
    weight REAL NOT NULL,
    min_score REAL NOT NULL,
    max_score REAL NOT NULL,
    evidence_required INTEGER NOT NULL,
    UNIQUE(question_id, criterion_code),
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
)
"""

WEIGHT_CONFIG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weight_configs (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL UNIQUE,
    confidence_low REAL NOT NULL,
    confidence_mid_start REAL NOT NULL,
    confidence_mid_end REAL NOT NULL,
    confidence_high REAL NOT NULL,
    max_followups INTEGER NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
)
"""

INTERVIEW_SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    status TEXT NOT NULL,
    question_index INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    average_score REAL,
    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY(candidate_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

CANDIDATE_ANSWER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS candidate_answers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    answer_order INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
)
"""

FOLLOWUP_QUESTION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS followup_questions (
    id TEXT PRIMARY KEY,
    answer_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    purpose TEXT NOT NULL,
    linked_criteria_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(answer_id) REFERENCES candidate_answers(id) ON DELETE CASCADE
)
"""

FOLLOWUP_ANSWER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS followup_answers (
    id TEXT PRIMARY KEY,
    followup_question_id TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    FOREIGN KEY(followup_question_id) REFERENCES followup_questions(id) ON DELETE CASCADE
)
"""

EVALUATION_RESULT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS evaluation_results (
    id TEXT PRIMARY KEY,
    candidate_answer_id TEXT NOT NULL,
    followup_answer_id TEXT,
    replaces_evaluation_id TEXT,
    raw_score REAL NOT NULL,
    max_score REAL NOT NULL,
    normalized_score REAL NOT NULL,
    percentage REAL NOT NULL,
    confidence_score REAL NOT NULL,
    confidence_band TEXT NOT NULL,
    finalize_decision TEXT NOT NULL,
    criteria_results_json TEXT NOT NULL,
    feedback_json TEXT NOT NULL,
    evidence_references_json TEXT NOT NULL,
    model_metadata_json TEXT NOT NULL,
    audit_payload_json TEXT NOT NULL,
    final_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(candidate_answer_id) REFERENCES candidate_answers(id) ON DELETE CASCADE,
    FOREIGN KEY(followup_answer_id) REFERENCES followup_answers(id) ON DELETE SET NULL,
    FOREIGN KEY(replaces_evaluation_id) REFERENCES evaluation_results(id) ON DELETE SET NULL
)
"""

AUDIT_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    evaluation_result_id TEXT NOT NULL,
    context_id TEXT,
    event_type TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(evaluation_result_id) REFERENCES evaluation_results(id) ON DELETE CASCADE,
    FOREIGN KEY(context_id) REFERENCES question_contexts(id) ON DELETE SET NULL
)
"""


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with dictionary-style row access."""

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the tables required by the MVP application slices."""

    connection.execute(USER_TABLE_SQL)
    connection.execute(TOPIC_TABLE_SQL)
    connection.execute(QUESTION_TABLE_SQL)
    connection.execute(QUESTION_CONTEXT_TABLE_SQL)
    connection.execute(RUBRIC_CRITERION_TABLE_SQL)
    connection.execute(WEIGHT_CONFIG_TABLE_SQL)
    connection.execute(INTERVIEW_SESSION_TABLE_SQL)
    connection.execute(CANDIDATE_ANSWER_TABLE_SQL)
    connection.execute(FOLLOWUP_QUESTION_TABLE_SQL)
    connection.execute(FOLLOWUP_ANSWER_TABLE_SQL)
    connection.execute(EVALUATION_RESULT_TABLE_SQL)
    connection.execute(AUDIT_EVENT_TABLE_SQL)
    connection.commit()
