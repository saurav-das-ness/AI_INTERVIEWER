"""Interview routes for candidate session management and answer evaluation."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_interview_service, get_reporting_service
from app.models.schemas.interview import (
    AnswerSubmissionResponse,
    SessionQuestionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SubmitAnswerRequest,
    SubmitFollowupRequest,
)
from app.models.schemas.reporting import SessionSummaryResponse
from app.services.interview.service import InterviewError, InterviewService
from app.services.reporting.service import ReportingService


router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/sessions", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: SessionStartRequest,
    interview_service: InterviewService = Depends(get_interview_service),
) -> SessionStartResponse:
    """Start a candidate interview session for a topic."""

    try:
        return interview_service.start_session(payload)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/current-question", response_model=SessionQuestionResponse)
def get_current_question(
    session_id: str,
    interview_service: InterviewService = Depends(get_interview_service),
) -> SessionQuestionResponse:
    """Return the current question for a live interview session."""

    try:
        return interview_service.get_current_question(session_id)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/answers", response_model=AnswerSubmissionResponse)
def submit_answer(
    payload: SubmitAnswerRequest,
    interview_service: InterviewService = Depends(get_interview_service),
) -> AnswerSubmissionResponse:
    """Submit a primary candidate answer and evaluate it."""

    try:
        return interview_service.submit_answer(payload)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/followups", response_model=AnswerSubmissionResponse)
def submit_followup(
    payload: SubmitFollowupRequest,
    interview_service: InterviewService = Depends(get_interview_service),
) -> AnswerSubmissionResponse:
    """Submit a follow-up answer and finalize evaluation."""

    try:
        return interview_service.submit_followup(payload)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
def get_session_summary(
    session_id: str,
    reporting_service: ReportingService = Depends(get_reporting_service),
) -> SessionSummaryResponse:
    """Return a candidate-safe session summary after completion."""

    try:
        return reporting_service.get_session_summary(session_id)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
