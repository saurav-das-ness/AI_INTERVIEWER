"""History (candidate) and review/audit (admin) views over completed sessions."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from app.api.dependencies import get_ingestion_service, get_reporting_service
from app.services.interview.service import InterviewError
from streamlit_app.components import confidence_badge, render_admin_evaluation_detail


def render_history_tab(user: dict) -> None:
    reporting_service = get_reporting_service()
    ingestion_service = get_ingestion_service()

    summaries = reporting_service.list_session_summaries(candidate_id=user["id"])
    if not summaries:
        st.info("No completed sessions yet — finish a practice run to see it here.")
        return

    topics_by_id = {topic.id: topic.topic_name for topic in ingestion_service.list_topics(include_unpublished=True)}
    summaries = sorted(summaries, key=lambda s: s.started_at_utc, reverse=True)

    for summary in summaries:
        topic_name = topics_by_id.get(summary.topic_id, summary.topic_id)
        label = f"{topic_name} · {summary.started_at_utc:%d %b %Y}"
        with st.expander(label):
            cols = st.columns(2)
            cols[0].metric("Questions", summary.question_count)
            cols[1].metric("Follow-ups", sum(a.followups_used for a in summary.answers))

            for answer in summary.answers:
                row = st.columns([3, 1])
                row[0].write(answer.question_code)
                with row[1]:
                    confidence_badge(answer.confidence_band)


def render_reviews_tab() -> None:
    reporting_service = get_reporting_service()

    summaries = reporting_service.list_session_summaries(candidate_id=None)
    if not summaries:
        st.info("No completed sessions to review yet.")
        return

    summaries = sorted(summaries, key=lambda s: s.started_at_utc, reverse=True)
    # include session_id suffix to guarantee unique labels
    options = {
        f"{s.candidate_id} · {s.started_at_utc:%d %b %Y %H:%M} · {s.average_score_percentage:.0f}% [{s.session_id[:8]}]": s.session_id
        for s in summaries
    }
    selected_label = st.selectbox("Session", options=list(options.keys()))
    session_id = options[selected_label]

    try:
        review = reporting_service.get_admin_session_review(session_id)
    except InterviewError as exc:
        st.error(str(exc))
        return

    cols = st.columns(3)
    cols[0].metric("Candidate", review.candidate_id)
    cols[1].metric("Score", f"{review.average_score_percentage:.0f}%")
    cols[2].metric("Questions", review.question_count)

    by_answer: dict[str, list[dict]] = defaultdict(list)
    for evaluation in review.evaluations:
        by_answer[evaluation["answer_id"]].append(evaluation)

    for evaluations in by_answer.values():
        question_code = evaluations[0]["question_code"]
        with st.expander(f"{question_code} — {evaluations[-1]['score_percentage']:.0f}%"):
            for evaluation in evaluations:
                render_admin_evaluation_detail(evaluation)
                st.divider()

    st.download_button(
        "Export audit JSON",
        data=review.model_dump_json(indent=2),
        file_name=f"review_{session_id}.json",
        mime="application/json",
    )
