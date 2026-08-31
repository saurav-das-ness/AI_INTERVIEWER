"""Shared rendering helpers for candidate feedback, scores, and evidence."""

from __future__ import annotations

import streamlit as st

_BAND_COLOR = {"low": "red", "mid": "orange", "high": "green"}


def confidence_badge(band: str) -> None:
    st.badge(f"{band} confidence", color=_BAND_COLOR.get(band, "gray"))


def render_criteria_breakdown(criteria_results: list[dict]) -> None:
    for criterion in criteria_results:
        max_score = float(criterion["max_score"]) or 1.0
        ratio = min(max(float(criterion["score_awarded"]) / max_score, 0.0), 1.0)
        st.caption(f"{criterion['criterion_name']} · weight {criterion['weight']:.2f}")
        st.progress(ratio, text=f"{criterion['score_awarded']:.1f} / {criterion['max_score']:.0f}")
        st.caption(criterion["reasoning"])


def render_evidence_chips(evidence_references: list[dict]) -> None:
    if not evidence_references:
        st.caption("No supporting evidence retrieved.")
        return
    for evidence in evidence_references:
        st.caption(
            f"{evidence.get('context_code', 'unknown')} · {evidence.get('source_type', '')} "
            f"· relevance {float(evidence.get('relevance_score', 0)):.2f}"
        )


def render_candidate_feedback_card(evaluation) -> None:
    """Render a candidate-safe score card for a CandidateEvaluationResponse."""

    with st.container(border=True):
        header_left, header_right = st.columns([3, 1])
        header_left.markdown("**Feedback**")
        with header_right:
            confidence_badge(evaluation.confidence_band)

        st.write(evaluation.summary)

        if evaluation.strengths:
            st.markdown("**Strengths**")
            for item in evaluation.strengths:
                st.caption(f"- {item}")
        if evaluation.gaps:
            st.markdown("**Gaps**")
            for item in evaluation.gaps:
                st.caption(f"- {item}")

        chunks = getattr(evaluation, "evidence_chunks", None) or []
        if chunks:
            with st.expander(f"Reference material used ({len(chunks)} chunk(s))", expanded=False):
                for i, chunk in enumerate(chunks, start=1):
                    label = chunk.source_label if hasattr(chunk, "source_label") else chunk.get("source_label", "Reference")
                    excerpt = chunk.excerpt if hasattr(chunk, "excerpt") else chunk.get("excerpt", "")
                    score = chunk.relevance_score if hasattr(chunk, "relevance_score") else chunk.get("relevance_score", 0.0)
                    st.markdown(f"**Chunk {i} — {label}** · relevance {score:.2f}")
                    st.caption(excerpt)
                    if i < len(chunks):
                        st.divider()


def render_session_summary(summary, *, on_new_session=None) -> None:
    """Render the end-of-session summary card (score, chart, focus areas)."""

    with st.container(border=True):
        cols = st.columns(2)
        cols[0].metric("Answered", f"{summary.question_count}")
        total_followups = sum(answer.followups_used for answer in summary.answers)
        cols[1].metric("Follow-ups used", f"{total_followups}")

        if summary.overall_strengths:
            st.markdown("**Strongest areas**")
            st.caption(", ".join(summary.overall_strengths))
        if summary.overall_gaps:
            st.markdown("**Focus next**")
            st.caption(", ".join(summary.overall_gaps))

        st.download_button(
            "Download report (JSON)",
            data=summary.model_dump_json(indent=2),
            file_name=f"session_{summary.session_id}.json",
            mime="application/json",
        )
        if on_new_session is not None and st.button("Start a new session"):
            on_new_session()


def render_import_messages(messages: list) -> None:
    for message in messages:
        location = ""
        if message.row_number is not None:
            location += f"row {message.row_number} "
        if message.field_name is not None:
            location += f"({message.field_name}) "
        text = f"{location}{message.message}".strip()
        if message.severity == "error":
            st.error(text, icon=":material/error:")
        else:
            st.warning(text, icon=":material/warning:")


def render_admin_evaluation_detail(evaluation: dict) -> None:
    """Render one evaluation entry (initial or rescored) inside an admin review."""

    header_left, header_right = st.columns([3, 1])
    if not evaluation.get("final_version", True):
        label = "Initial (superseded)"
    elif evaluation.get("followups_used", 0):
        label = "Rescored"
    else:
        label = "Final"
    header_left.markdown(f"**{label} · {evaluation['score_percentage']:.0f} / 100**")
    with header_right:
        confidence_badge(evaluation["confidence_band"])

    render_criteria_breakdown(evaluation["criteria_results"])

    st.markdown("**Evidence used**")
    render_evidence_chips(evaluation["evidence_references"])

    thresholds = evaluation.get("thresholds_applied", {})
    if thresholds:
        st.caption(
            "Thresholds applied — low < {low:.2f} · mid {mid_start:.2f}-{mid_end:.2f} · high > {high:.2f}".format(
                low=thresholds.get("low", 0),
                mid_start=thresholds.get("mid_start", 0),
                mid_end=thresholds.get("mid_end", 0),
                high=thresholds.get("high", 0),
            )
        )

    metadata = evaluation.get("model_metadata", {})
    if metadata:
        st.caption(
            f"{metadata.get('provider', 'unknown')} · {metadata.get('model_name', '')} "
            f"· prompt {metadata.get('prompt_version', '')}"
        )
