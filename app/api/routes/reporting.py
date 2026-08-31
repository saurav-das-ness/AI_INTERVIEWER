"""Reporting routes for admin and candidate session review."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_reporting_service
from app.models.schemas.reporting import AdminEvaluationReviewResponse, SessionSummaryResponse
from app.services.interview.service import InterviewError
from app.services.reporting.service import ReportingService


router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/sessions", response_model=list[SessionSummaryResponse])
def list_session_summaries(
    candidate_id: str | None = Query(default=None),
    reporting_service: ReportingService = Depends(get_reporting_service),
) -> list[SessionSummaryResponse]:
    """Return session summaries for candidate or admin review."""

    return reporting_service.list_session_summaries(candidate_id=candidate_id)


@router.get("/sessions/{session_id}", response_model=AdminEvaluationReviewResponse)
def get_admin_session_review(
    session_id: str,
    reporting_service: ReportingService = Depends(get_reporting_service),
) -> AdminEvaluationReviewResponse:
    """Return detailed admin review data for a completed session."""

    try:
        return reporting_service.get_admin_session_review(session_id)
    except InterviewError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
