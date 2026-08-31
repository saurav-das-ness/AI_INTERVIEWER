"""Shared sidebar auth widget for Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_INTERVIEW_STATE_KEYS = ("active_session_id", "pending_followup")

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

_SAMPLE_CSVS = [
    ("System Design (MCQ + Short)", "system_design_questions.csv"),
    ("System Design (Long Answer)", "system_design_long_answer_questions.csv"),
    ("System Design (Text)", "system_design_text.csv"),
    ("Neural Networks", "neural_networks_questions.csv"),
]


def _render_sample_downloads() -> None:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Sample question files**")
    for label, filename in _SAMPLE_CSVS:
        path = _PROJECT_ROOT / filename
        if path.exists():
            st.sidebar.download_button(
                label=f"⬇ {label}",
                data=path.read_bytes(),
                file_name=filename,
                mime="text/csv",
                key=f"dl_{filename}",
            )


def render_session_sidebar() -> None:
    """Show the signed-in user and a logout control in the sidebar."""
    user = st.session_state.get("current_user")
    if user is None:
        _render_sample_downloads()
        return

    with st.sidebar:
        st.caption(f"Signed in as {user['email']} ({user['role']})")
        if st.button("Logout"):
            st.session_state["current_user"] = None
            for key in _INTERVIEW_STATE_KEYS:
                st.session_state.pop(key, None)
            st.rerun()

    _render_sample_downloads()
