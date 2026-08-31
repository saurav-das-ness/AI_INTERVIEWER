"""Streamlit entrypoint: login/registration and the candidate practice workspace."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.dependencies import get_auth_service
from app.models.domain.user import UserRole
from app.models.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth.service import AuthConflictError, AuthenticationError
from streamlit_app.auth_ui import render_session_sidebar
from streamlit_app.interview_flow import render_practice_tab
from streamlit_app.report_views import render_history_tab


st.set_page_config(page_title="AI Interview Tool", page_icon="AI", layout="wide")


def _ensure_state() -> None:
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("prefs", {"expand_breakdown": False, "high_contrast": False})


def _login_panel() -> None:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            try:
                user = get_auth_service().authenticate(LoginRequest(email=email, password=password))
            except AuthenticationError as exc:
                st.error(str(exc))
            else:
                st.session_state["current_user"] = {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role.value,
                }
                st.rerun()


def _register_panel() -> None:
    with st.form("register_form"):
        email = st.text_input("Registration email")
        password = st.text_input("Registration password", type="password")
        role = st.selectbox("Role", options=[role.value for role in UserRole])
        submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                user = get_auth_service().register_user(
                    RegisterRequest(email=email, password=password, role=UserRole(role))
                )
            except AuthConflictError as exc:
                st.error(str(exc))
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Created {user.role.value} account for {user.email}. You can sign in now.")


def _render_login() -> None:
    st.title("AI Interview Tool")
    st.caption("Text-first interview practice with admin-managed question banks and grounded scoring.")

    _, center, _ = st.columns([1, 2, 1])
    with center, st.container(border=True):
        st.subheader("Sign in to practice")
        sign_in_tab, create_account_tab = st.tabs(["Sign in", "Create account"])
        with sign_in_tab:
            _login_panel()
        with create_account_tab:
            _register_panel()


def _render_settings_tab(user: dict) -> None:
    st.text_input("Display name", value=user["email"], disabled=True)
    st.caption("Profile editing isn't available yet — contact an admin to update account details.")

    prefs = st.session_state["prefs"]
    prefs["expand_breakdown"] = st.checkbox("Expand criterion breakdown by default", value=prefs["expand_breakdown"])
    prefs["high_contrast"] = st.checkbox("Larger text / high contrast", value=prefs["high_contrast"])

    if st.button("Sign out"):
        st.session_state["current_user"] = None
        st.rerun()


def render_home() -> None:
    current_user = st.session_state.get("current_user")
    if current_user is None:
        _render_login()
        return

    if current_user["role"] == UserRole.ADMIN.value:
        st.title("AI Interview Tool")
        st.info(f"Signed in as {current_user['email']} (admin)")
        st.page_link("pages/1_Admin.py", label="Go to Admin", icon=":material/admin_panel_settings:")
        return

    st.title("AI Interview Tool")
    practice_tab, history_tab, settings_tab = st.tabs(["Practice", "History", "Settings"])
    with practice_tab:
        render_practice_tab(current_user)
    with history_tab:
        render_history_tab(current_user)
    with settings_tab:
        _render_settings_tab(current_user)


def _build_pages(role: str | None) -> list[st.Page]:
    pages = [st.Page(render_home, title="Home", icon=":material/home:", default=True)]
    if role == UserRole.ADMIN.value:
        pages.append(st.Page("pages/1_Admin.py", title="Admin", icon=":material/admin_panel_settings:"))
    return pages


_ensure_state()
render_session_sidebar()

_current_user = st.session_state.get("current_user")
_role = _current_user["role"] if _current_user else None

navigation = st.navigation(_build_pages(_role), position="top")
navigation.run()
