from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.repositories.assessment_repository import AssessmentRepository
from app.schemas.assessment import (AssessmentSummaryResponse, ComparisonResponse,
                                    PersistedRequirementResult, SubmissionResponse,
                                    TenderDetailResponse, TenderResponse)
from app.services.assessment.assessment_service import AssessmentService
from app.services.assessment.errors import AssessmentInputError, AssessmentNotFoundError, AssessmentStateError
from app.services.assessment.prototype_evidence import PrototypeEvidenceProvider


router = APIRouter(tags=["assessments"])


def get_assessment_service():
    return AssessmentService(AssessmentRepository(), PrototypeEvidenceProvider(get_settings()))


Service = Annotated[AssessmentService, Depends(get_assessment_service)]


def call(operation, *args):
    try:
        return operation(*args)
    except AssessmentNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except AssessmentStateError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    except AssessmentInputError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail="Assessment operation failed") from exc


@router.get("/tenders", response_model=list[TenderResponse])
def tenders(service: Service):
    return call(service.repository.tenders)


@router.get("/tenders/{tender_id}", response_model=TenderDetailResponse)
def tender(tender_id: str, service: Service):
    return call(service.repository.tender, tender_id)


@router.get("/tenders/{tender_id}/submissions", response_model=list[SubmissionResponse])
def submissions(tender_id: str, service: Service):
    return call(service.repository.submissions, tender_id)


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def submission(submission_id: str, service: Service):
    return call(service.repository.submission, submission_id)


@router.post("/submissions/{submission_id}/assess", response_model=AssessmentSummaryResponse)
def assess(submission_id: str, service: Service):
    return call(service.run_assessment, submission_id)


@router.get("/submissions/{submission_id}/assessment", response_model=AssessmentSummaryResponse)
def assessment(submission_id: str, service: Service):
    return call(service.repository.assessment, submission_id)


@router.get("/submissions/{submission_id}/requirement-results", response_model=list[PersistedRequirementResult])
def requirements(submission_id: str, service: Service):
    return call(service.repository.assessment, submission_id).requirement_results


@router.get("/tenders/{tender_id}/comparison", response_model=ComparisonResponse)
def comparison(tender_id: str, service: Service):
    return call(service.comparison, tender_id)
