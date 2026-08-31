"""Streamlit admin workspace: topics, question bank, reference PDFs, rubric, and reviews."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.dependencies import get_ingestion_service
from app.models.domain.user import UserRole
from app.services.ingestion.service import IngestionError
from streamlit_app.components import render_import_messages
from streamlit_app.report_views import render_reviews_tab


def _require_admin() -> dict[str, str] | None:
    user = st.session_state.get("current_user")
    if user is None:
        st.warning("Sign in from the Home page first.")
        return None
    if user["role"] != UserRole.ADMIN.value:
        st.error("Admin access only.")
        return None
    return user


def _render_topics_tab() -> None:
    ingestion_service = get_ingestion_service()
    topics = ingestion_service.list_topics(include_unpublished=True)

    if not topics:
        st.info("No topics yet — import questions from the **Import Questions** tab to create one.")
        return

    st.caption(f"{len(topics)} topic(s) — toggle to make a topic available to candidates.")
    for topic in topics:
        with st.container(border=True):
            left, mid, right = st.columns([4, 1, 1])
            left.markdown(f"**{topic.topic_name}**")
            left.caption(f"Code: `{topic.topic_code}` · {topic.question_count} questions")
            mid.badge("Published" if topic.published else "Draft", color="green" if topic.published else "gray")
            if right.button("Toggle", key=f"toggle_{topic.id}"):
                ingestion_service.set_topic_publication(topic.id, not topic.published)
                st.rerun()


def _show_csv_format_hint() -> None:
    with st.expander("Required CSV column format"):
        st.code(
            "topic_code, topic_name, question_code, question_text, question_type, difficulty,\n"
            "expected_answer_summary, question_prompt_notes,\n"
            "followup_enabled, max_followups,\n"
            "confidence_low, confidence_mid_start, confidence_mid_end, confidence_high,\n"
            "published",
            language="text",
        )
        st.caption("question_type values: MCQ | TrueFalse | ShortAnswer")
        st.caption("difficulty values: easy | medium | hard")
        st.caption("If Course code and Course name are filled above, topic_code/topic_name columns are optional.")


def _render_import_questions_tab(user: dict) -> None:
    ingestion_service = get_ingestion_service()

    st.subheader("Course details")
    st.caption("Required for CSV and Excel imports. JSON files carry topic data internally.")
    col_a, col_b = st.columns(2)
    topic_code_override = col_a.text_input(
        "Course code",
        placeholder="e.g. neural_networks",
        key="import_topic_code",
        help="Short unique identifier — lowercase, underscores, no spaces.",
    ).strip() or None
    topic_name_override = col_b.text_input(
        "Course name",
        placeholder="e.g. Neural Networks",
        key="import_topic_name",
        help="Full display name shown to candidates.",
    ).strip() or None

    st.subheader("Upload question file")
    st.caption("Supported: CSV, Excel (.xlsx / .xlsm), JSON.  PDFs go in the **Reference PDFs** tab.")
    uploaded_file = st.file_uploader(
        "Choose file",
        type=["json", "csv", "xlsx", "xlsm"],
        key="qbank_upload",
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        st.info("Upload a CSV, Excel, or JSON file above to preview and import questions.")
        _show_csv_format_hint()
        return

    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    suffix = Path(file_name).suffix

    if suffix == ".json" and (topic_code_override or topic_name_override):
        st.info("Topic identity is embedded in JSON files — Course code and Course name above are ignored for JSON.")

    try:
        preview = ingestion_service.preview_uploaded_file(
            uploaded_file.name,
            raw_bytes,
            topic_code=topic_code_override,
            topic_name=topic_name_override,
        )
    except Exception as exc:
        st.error(str(exc))
        return

    st.subheader("Import preview")
    c = st.columns(4)
    c[0].metric("Topics", preview.topic_count)
    c[1].metric("Questions", preview.question_count)
    c[2].metric("Contexts", preview.context_count)
    c[3].metric("Rubric criteria", preview.rubric_count)

    if preview.messages:
        st.markdown(f"**Validation — {len(preview.messages)} issue(s)**")
        render_import_messages(preview.messages)
    else:
        st.success("File is valid and ready to import.")

    if not preview.valid:
        st.warning("Fix the issues above before importing.")
        return

    if suffix in {".csv", ".xlsx", ".xlsm"} and not (topic_code_override and topic_name_override):
        st.warning("Enter both **Course code** and **Course name** above before importing.")
        return

    try:
        if st.button("Apply import", type="primary"):
            result = ingestion_service.apply_uploaded_file(
                file_name=uploaded_file.name,
                file_bytes=raw_bytes,
                created_by=user["id"],
                topic_code=topic_code_override,
                topic_name=topic_name_override,
            )
            st.success(
                f"Imported **{result.topic_name}** — "
                f"{result.question_count} questions, {result.rubric_count} rubric criteria."
            )
            st.balloons()
    except (IngestionError, ValueError) as exc:
        st.error(str(exc))

    st.divider()
    st.subheader("Browse existing questions")
    topics = ingestion_service.list_topics(include_unpublished=True)
    if not topics:
        return

    topic_options = {f"{t.topic_name} ({t.topic_code})": t.id for t in topics}
    selected_label = st.selectbox("Select course", options=list(topic_options.keys()), key="qbank_topic")
    questions = ingestion_service.list_questions(topic_options[selected_label])
    if not questions:
        st.info("This course has no questions yet.")
        return

    st.dataframe(
        [
            {
                "Code": q.question_code,
                "Question": q.question_text[:90] + ("..." if len(q.question_text) > 90 else ""),
                "Type": q.question_type,
                "Difficulty": q.difficulty,
                "Follow-ups": "on" if q.followup_enabled else "off",
                "Published": "yes" if q.published else "no",
            }
            for q in questions
        ],
        hide_index=True,
        use_container_width=True,
    )


def _render_reference_pdfs_tab(user: dict) -> None:
    ingestion_service = get_ingestion_service()

    st.subheader("Upload reference PDF")
    st.caption(
        "PDFs are split into chunks and indexed into the vector store (ChromaDB). "
        "During evaluation, candidate answers are matched against these chunks — "
        "not the LLM's general knowledge."
    )

    topics = ingestion_service.list_topics(include_unpublished=True)
    if not topics:
        st.warning("No courses found. Import questions first, then attach a reference PDF.")
        return

    topic_options = {f"{t.topic_name}  —  {t.topic_code}": t for t in topics}
    selected_topic_label = st.selectbox("Course this PDF belongs to", options=list(topic_options.keys()), key="pdf_topic")
    selected_topic = topic_options[selected_topic_label]

    all_questions = ingestion_service.list_questions(selected_topic.id)
    question_options: dict[str, str | None] = {"— No specific question (course-level context) —": None}
    question_options.update({
        f"{q.question_code}  —  {q.question_text[:60]}": q.question_code
        for q in all_questions
    })
    selected_q_label = st.selectbox(
        "Link to a specific question (optional)",
        options=list(question_options.keys()),
        key="pdf_question",
        help="Leave as course-level to use this PDF for all questions in the course.",
    )
    pdf_question_code: str | None = question_options[selected_q_label]

    pdf_published = st.checkbox(
        "Publish PDF context immediately",
        value=True,
        help="Unpublished context is stored but not used in scoring until published.",
    )

    st.subheader("Choose PDF file")
    uploaded_pdf = st.file_uploader("PDF", type=["pdf"], key="pdf_upload", label_visibility="collapsed")

    if uploaded_pdf is None:
        st.info("Upload a PDF above. It will be split into text chunks and indexed for RAG-based scoring.")
        return

    raw_bytes = uploaded_pdf.getvalue()
    try:
        preview = ingestion_service.preview_uploaded_file(uploaded_pdf.name, raw_bytes)
    except Exception as exc:
        st.error(str(exc))
        return

    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.metric("Extractable text chunks", preview.context_count)
        col2.metric("File size", f"{len(raw_bytes) / 1024:.1f} KB")
        if preview.context_count == 0:
            st.error("No text could be extracted. This may be a scanned/image-only PDF.")
            return
        if preview.messages:
            render_import_messages(preview.messages)

    scope = f"question `{pdf_question_code}`" if pdf_question_code else f"course `{selected_topic.topic_code}`"
    st.info(f"**{preview.context_count}** chunks will be indexed as context for **{scope}**.")

    try:
        if st.button("Index PDF", type="primary"):
            result = ingestion_service.apply_uploaded_file(
                file_name=uploaded_pdf.name,
                file_bytes=raw_bytes,
                created_by=user["id"],
                topic_code=selected_topic.topic_code,
                question_code=pdf_question_code,
                published=pdf_published,
            )
            st.success(
                f"Indexed **{result.context_count}** chunk(s) into the vector store "
                f"for course **{result.topic_name}**."
            )
            st.balloons()
    except (IngestionError, ValueError) as exc:
        st.error(str(exc))


def _render_rubric_tab() -> None:
    ingestion_service = get_ingestion_service()
    topics = ingestion_service.list_topics(include_unpublished=True)
    if not topics:
        st.info("No courses yet — import questions first.")
        return

    topic_options = {f"{t.topic_name} ({t.topic_code})": t.id for t in topics}
    selected_topic_label = st.selectbox("Course", options=list(topic_options.keys()), key="rubric_topic")
    questions = ingestion_service.list_questions(topic_options[selected_topic_label])
    if not questions:
        st.info("This course has no questions yet.")
        return

    question_options = {f"{q.question_code} — {q.question_text[:60]}": q.id for q in questions}
    selected_question_label = st.selectbox("Question", options=list(question_options.keys()), key="rubric_question")
    question_id = question_options[selected_question_label]

    criteria = ingestion_service.get_rubric(question_id)
    weight_config = ingestion_service.get_weight_config(question_id)
    if not criteria or weight_config is None:
        st.info("This question has no rubric or weight configuration yet.")
        return

    st.markdown("**Criteria weights** (must sum to 1.00)")
    weight_inputs: dict[str, float] = {}
    for criterion in criteria:
        weight_inputs[criterion.id] = st.slider(
            criterion.criterion_name,
            min_value=0.0,
            max_value=1.0,
            value=float(criterion.weight),
            step=0.05,
            key=f"weight_{criterion.id}",
        )
    total_weight = sum(weight_inputs.values())
    weight_ok = abs(total_weight - 1.0) <= 0.01
    _color = "green" if weight_ok else "red"
    st.markdown(f"Sum: :{_color}[**{total_weight:.2f}**]")

    st.markdown("**Confidence bands**")
    st.caption("Low → flagged low confidence.  Probe range → follow-up triggered.  High → high confidence.")
    bc = st.columns(4)
    low = bc[0].number_input("Low <", value=float(weight_config.confidence_low), min_value=0.0, max_value=1.0, step=0.05)
    mid_start = bc[1].number_input("Probe from", value=float(weight_config.confidence_mid_start), min_value=0.0, max_value=1.0, step=0.05)
    mid_end = bc[2].number_input("Probe to", value=float(weight_config.confidence_mid_end), min_value=0.0, max_value=1.0, step=0.05)
    high = bc[3].number_input("High >", value=float(weight_config.confidence_high), min_value=0.0, max_value=1.0, step=0.05)
    max_followups = st.number_input("Max follow-ups (0–3)", value=int(weight_config.max_followups), min_value=0, max_value=3, step=1)

    thresholds_ordered = low <= mid_start <= mid_end <= high
    if not thresholds_ordered:
        st.warning("Thresholds must satisfy: Low <= Probe from <= Probe to <= High.")

    if st.button("Save rubric", type="primary", disabled=not (thresholds_ordered and weight_ok)):
        ingestion_service.update_rubric_weights(weight_inputs)
        ingestion_service.update_weight_config(
            question_id,
            confidence_low=low,
            confidence_mid_start=mid_start,
            confidence_mid_end=mid_end,
            confidence_high=high,
            max_followups=int(max_followups),
        )
        st.success("Rubric and thresholds saved.")


st.title("Admin — Content Management")
_user = _require_admin()
if _user is None:
    st.stop()

topics_tab, import_tab, pdfs_tab, rubric_tab, reviews_tab = st.tabs(
    ["Topics", "Import Questions", "Reference PDFs", "Rubric & Thresholds", "Reviews"]
)
with topics_tab:
    _render_topics_tab()
with import_tab:
    _render_import_questions_tab(_user)
with pdfs_tab:
    _render_reference_pdfs_tab(_user)
with rubric_tab:
    _render_rubric_tab()
with reviews_tab:
    render_reviews_tab()
