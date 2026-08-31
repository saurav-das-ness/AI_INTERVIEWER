"""Administrative routes for content import and topic management."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_ingestion_service
from app.models.schemas.admin import (
    CsvImportRequest,
    ImportApplyResponse,
    ImportPreviewResponse,
    JsonImportRequest,
    PublishTopicRequest,
    TopicSummaryResponse,
)
from app.services.ingestion.service import IngestionError, IngestionService


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/topics", response_model=list[TopicSummaryResponse])
def list_topics(ingestion_service: IngestionService = Depends(get_ingestion_service)) -> list[TopicSummaryResponse]:
    """Return all topics, including unpublished ones, for admin review."""

    topics = ingestion_service.list_topics(include_unpublished=True)
    return [TopicSummaryResponse.model_validate(topic) for topic in topics]


@router.post("/import/json/preview", response_model=ImportPreviewResponse)
def preview_json_import(
    payload: JsonImportRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportPreviewResponse:
    """Preview a JSON bulk import without persisting it."""

    return ingestion_service.preview_json_package(payload.package)


@router.post("/import/json/apply", response_model=ImportApplyResponse, status_code=status.HTTP_201_CREATED)
def apply_json_import(
    payload: JsonImportRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportApplyResponse:
    """Persist a JSON bulk import."""

    try:
        return ingestion_service.apply_json_package(payload.package, payload.created_by)
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import/csv/preview", response_model=ImportPreviewResponse)
def preview_csv_import(
    payload: CsvImportRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportPreviewResponse:
    """Preview a CSV question-bank import without persisting it."""

    return ingestion_service.preview_csv_text(payload.csv_text)


@router.post("/import/csv/apply", response_model=ImportApplyResponse, status_code=status.HTTP_201_CREATED)
def apply_csv_import(
    payload: CsvImportRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportApplyResponse:
    """Persist a CSV question-bank import."""

    try:
        return ingestion_service.apply_csv_text(payload.csv_text, payload.created_by)
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/topics/{topic_id}/publish", response_model=TopicSummaryResponse)
def publish_topic(
    topic_id: str,
    payload: PublishTopicRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> TopicSummaryResponse:
    """Toggle topic publication state."""

    try:
        topic = ingestion_service.set_topic_publication(topic_id, payload.published)
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TopicSummaryResponse.model_validate(topic)


@router.post("/import/files/preview", response_model=ImportPreviewResponse)
async def preview_uploaded_import(
    upload: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportPreviewResponse:
    """Preview CSV, Excel, JSON, or PDF uploads from multipart form data."""

    try:
        return ingestion_service.preview_uploaded_file(upload.filename or "upload.bin", await upload.read())
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/import/files/apply", response_model=ImportApplyResponse, status_code=status.HTTP_201_CREATED)
async def apply_uploaded_import(
    created_by: str = Form(...),
    topic_code: str | None = Form(default=None),
    question_code: str | None = Form(default=None),
    published: bool = Form(default=False),
    upload: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> ImportApplyResponse:
    """Persist CSV, Excel, JSON, or PDF uploads from multipart form data."""

    try:
        return ingestion_service.apply_uploaded_file(
            file_name=upload.filename or "upload.bin",
            file_bytes=await upload.read(),
            created_by=created_by,
            topic_code=topic_code,
            question_code=question_code,
            published=published,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
