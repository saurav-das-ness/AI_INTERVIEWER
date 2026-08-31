"""Candidate practice flow: dashboard, pre-flight, chat interview, and summary."""

from __future__ import annotations

import streamlit as st

from app.api.dependencies import get_ingestion_service, get_interview_service, get_reporting_service
from app.models.schemas.interview import SessionStartRequest, SubmitAnswerRequest, SubmitFollowupRequest
from app.services.interview.service import InterviewError
from streamlit_app.components import render_candidate_feedback_card, render_session_summary

_SESSION_KEYS = (
    "active_session_id",
    "pending_followup",
    "transcript",
    "question_number",
    "topic_question_count",
    "topic_name",
    "interview_complete",
)


def _reset_session_state() -> None:
    for key in _SESSION_KEYS:
        st.session_state.pop(key, None)
    st.session_state.pop("selected_topic_id", None)


def render_practice_tab(user: dict) -> None:
    ingestion_service = get_ingestion_service()
    interview_service = get_interview_service()
    reporting_service = get_reporting_service()

    if st.session_state.get("active_session_id"):
        _render_active_session(interview_service, reporting_service)
    elif st.session_state.get("selected_topic_id"):
        _render_preflight(user, ingestion_service, interview_service)
    else:
        _render_dashboard(user, ingestion_service, interview_service, reporting_service)


def _render_dashboard(user, ingestion_service, interview_service, reporting_service) -> None:
    completed = reporting_service.list_session_summaries(candidate_id=user["id"])
    all_sessions = interview_service.list_sessions(user["id"])
    in_progress = [session for session in all_sessions if session.status != "completed"]

    avg_score = round(sum(s.average_score_percentage for s in completed) / len(completed), 1) if completed else 0.0
    cols = st.columns(2)
    cols[0].metric("Sessions done", len(completed))
    cols[1].metric("In progress", len(in_progress))

    topics = ingestion_service.list_topics(include_unpublished=False)
    topics_by_id = {topic.id: topic for topic in topics}

    if in_progress:
        resume = in_progress[0]
        topic = topics_by_id.get(resume.topic_id)
        topic_name = topic.topic_name if topic else resume.topic_id
        total = min(topic.question_count, 5) if topic else max(resume.question_index, 1)
        with st.container(border=True):
            st.markdown(f"**Resume: {topic_name}**")
            st.progress(min(resume.question_index / total, 1.0) if total else 0.0, text=f"Question {resume.question_index + 1} of {total}")
            if st.button("Continue session"):
                st.session_state["active_session_id"] = resume.id
                st.session_state["topic_name"] = topic_name
                st.session_state["topic_question_count"] = total
                st.session_state["question_number"] = resume.question_index + 1
                st.session_state["transcript"] = []
                st.rerun()

    st.subheader("Available topics")
    if not topics:
        st.info("No published topics are available yet. Check back once an admin publishes one.")
        return

    grid = st.columns(2)
    for index, topic in enumerate(topics):
        with grid[index % 2].container(border=True):
            st.markdown(f"**{topic.topic_name}**")
            st.caption(f"{min(topic.question_count, 5)} questions · {topic.topic_code}")
            if st.button("Start", key=f"start_{topic.id}"):
                st.session_state["selected_topic_id"] = topic.id
                st.rerun()


def _render_preflight(user, ingestion_service, interview_service) -> None:
    topic_id = st.session_state["selected_topic_id"]
    topic = next((t for t in ingestion_service.list_topics(include_unpublished=False) if t.id == topic_id), None)
    if topic is None:
        st.session_state.pop("selected_topic_id", None)
        st.rerun()
        return

    st.subheader(f"Start interview: {topic.topic_name}")
    st.info(
        "One question at a time. Up to 3 follow-up probes if your answer needs more evidence. "
        "Feedback appears after each answer; the ideal answer is never shown mid-session."
    )
    st.caption(f"{min(topic.question_count, 5)} questions in this set")

    left, right = st.columns(2)
    if left.button("Begin session", type="primary"):
        try:
            session = interview_service.start_session(SessionStartRequest(candidate_id=user["id"], topic_id=topic.id))
        except InterviewError as exc:
            st.error(str(exc))
        else:
            st.session_state["active_session_id"] = session.session_id
            st.session_state["topic_name"] = topic.topic_name
            st.session_state["topic_question_count"] = min(topic.question_count, 5)
            st.session_state["question_number"] = 1
            st.session_state["transcript"] = [{"role": "assistant", "text": _format_question_prompt(session.question)}] if session.question else []
            st.rerun()
    if right.button("Cancel"):
        st.session_state.pop("selected_topic_id", None)
        st.rerun()


def _render_active_session(interview_service, reporting_service) -> None:
    session_id = st.session_state["active_session_id"]
    total = st.session_state.get("topic_question_count", 0)
    question_number = st.session_state.get("question_number", 1)
    pending_followup = st.session_state.get("pending_followup")

    header_left, header_right = st.columns([3, 1])
    header_left.subheader(st.session_state.get("topic_name", "Interview"))
    with header_right:
        st.caption(f"Q{question_number} of {total or '?'}")
    if total:
        st.progress(min((question_number - 1) / total, 1.0))

    for turn in st.session_state.get("transcript", []):
        with st.chat_message(turn["role"]):
            if turn.get("evaluation"):
                render_candidate_feedback_card(turn["evaluation"])
            else:
                st.write(turn["text"])

    if st.session_state.get("interview_complete"):
        summary = reporting_service.get_session_summary(session_id)
        st.divider()
        render_session_summary(summary, on_new_session=_reset_session_state)
        return

    if pending_followup:
        prompt = st.chat_input("Answer the follow-up...")
        if prompt:
            st.session_state["transcript"].append({"role": "user", "text": prompt})
            with st.status("Evaluating your follow-up...", expanded=False) as status:
                result = interview_service.submit_followup(
                    SubmitFollowupRequest(session_id=session_id, followup_id=pending_followup["followup_id"], answer_text=prompt)
                )
                status.update(label="Evaluation complete", state="complete")
            st.session_state["pending_followup"] = None
            _handle_result(result, question_number)
            st.rerun()
    else:
        prompt = st.chat_input("Your answer...")
        if prompt:
            current = interview_service.get_current_question(session_id)
            if current.question is None:
                st.error("This session has no active question.")
                return
            st.session_state["transcript"].append({"role": "user", "text": prompt})
            with st.status("Evaluating your answer...", expanded=False) as status:
                result = interview_service.submit_answer(
                    SubmitAnswerRequest(session_id=session_id, question_id=current.question.id, answer_text=prompt)
                )
                status.update(label="Evaluation complete", state="complete")
            _handle_result(result, question_number)
            st.rerun()


def _handle_result(result, question_number: int) -> None:
    if result.followup:
        st.session_state["pending_followup"] = result.followup.model_dump()
        st.session_state["transcript"].append(
            {"role": "assistant", "text": f"Follow-up {result.followup.followup_sequence} of {result.followup.max_followups}: {result.followup.prompt}"}
        )
        return

    if result.evaluation:
        st.session_state["transcript"].append({"role": "assistant", "text": result.evaluation.summary, "evaluation": result.evaluation})

    if result.interview_complete:
        st.session_state["interview_complete"] = True
    elif result.next_question:
        st.session_state["question_number"] = question_number + 1
        st.session_state["transcript"].append({"role": "assistant", "text": _format_question_prompt(result.next_question)})


def _format_question_prompt(question) -> str:
    """Render a question with compact question-linked context snippets."""

    base = question.question_text
    chunks = list(getattr(question, "grounding_chunks", []) or [])
    if not chunks:
        return base

    lines = [base, "", "Reference context:"]
    for chunk in chunks[:2]:
        excerpt = str(chunk.excerpt).strip()
        if len(excerpt) > 140:
            excerpt = f"{excerpt[:137]}..."
        lines.append(f"- {chunk.source_label}: {excerpt}")
    return "\n".join(lines)
