from fastapi import APIRouter

from app.api.v1.submission_documents import router as submission_documents_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.ingestion import router as ingestion_router


api_router = APIRouter()
api_router.include_router(submission_documents_router)
api_router.include_router(ingestion_router)
api_router.include_router(assessments_router)
