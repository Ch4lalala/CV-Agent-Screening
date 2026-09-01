from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.datastructures import UploadFile

from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.ai.client import AIClient, get_ai_client
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIStructuredOutputError,
)
from app.models.job import Job
from app.models.job_requirement import JobRequirement
from app.repositories import job_requirements, jobs
from app.schemas.job import JobCreate, JobResponse, JobUpdate
from app.schemas.job_requirement import (
    JobRequirementCreate,
    JobRequirementResponse,
    JobRequirementUpdate,
)
from app.schemas.job_import import JobDescriptionAnalysisRequest, JobImportDraft
from app.services import job_document_service, resume_service
from app.services.job_import_service import generate_job_import_draft

router = APIRouter(prefix="/jobs", tags=["jobs"])
AIClientDependency = Annotated[AIClient, Depends(get_ai_client)]


def _get_job_or_404(db: DatabaseSession, user: DevelopmentUser, job_id: int) -> Job:
    job = jobs.get_for_user(db, job_id=job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _get_requirement_or_404(
    db: DatabaseSession, job_id: int, requirement_id: int
) -> JobRequirement:
    requirement = job_requirements.get_for_job(
        db, job_id=job_id, requirement_id=requirement_id
    )
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job requirement not found",
        )
    return requirement


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, db: DatabaseSession, user: DevelopmentUser) -> Job:
    return jobs.create(db, user_id=user.id, data=data)


@router.get("", response_model=list[JobResponse])
def list_jobs(db: DatabaseSession, user: DevelopmentUser) -> list[Job]:
    return jobs.list_for_user(db, user_id=user.id)


@router.post("/analyze-description", response_model=JobImportDraft)
async def analyze_job_description(
    data: JobDescriptionAnalysisRequest,
    _: DevelopmentUser,
    ai_client: AIClientDependency,
) -> JobImportDraft:
    """Generate an editable draft without persisting the vacancy or requirements."""

    source_text = f"Job title:\n{data.title}\n\nJob description:\n{data.description}"
    try:
        draft = await generate_job_import_draft(source_text, ai_client=ai_client)
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured.",
        ) from exc
    except (AIProviderError, AIStructuredOutputError) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable.",
        ) from exc

    # Recruiter-entered vacancy details remain authoritative; AI supplies only the draft criteria.
    return draft.model_copy(
        update={
            "title": data.title,
            "description": data.description,
            "warnings": [
                warning
                for warning in draft.warnings
                if warning.type != "inferred_title"
            ],
        }
    )


@router.post("/import", response_model=JobImportDraft)
async def import_job_document(
    request: Request,
    _: DevelopmentUser,
    ai_client: AIClientDependency,
) -> JobImportDraft:
    content_type = request.headers.get("content-type", "").lower()
    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a job document using multipart/form-data.",
        )
    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A PDF, DOCX, or TXT job document is required.",
        )
    try:
        return await job_document_service.import_job_document(
            upload,
            ai_client=ai_client,
        )
    except job_document_service.UnsupportedJobDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except job_document_service.InvalidJobDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except job_document_service.JobDocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except job_document_service.NoReadableJobDocumentTextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured.",
        ) from exc
    except (AIProviderError, AIStructuredOutputError) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable.",
        ) from exc
    except job_document_service.JobDocumentProcessingError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to process the job document.",
        ) from exc
    finally:
        await upload.close()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: DatabaseSession, user: DevelopmentUser) -> Job:
    return _get_job_or_404(db, user, job_id)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int, data: JobUpdate, db: DatabaseSession, user: DevelopmentUser
) -> Job:
    job = _get_job_or_404(db, user, job_id)
    return jobs.update(db, job=job, data=data)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: DatabaseSession, user: DevelopmentUser) -> Response:
    job = _get_job_or_404(db, user, job_id)
    try:
        resume_service.delete_job_and_resumes(db, job=job)
    except resume_service.ResumeStorageError as exc:
        raise HTTPException(
            status_code=500, detail="Unable to remove stored resume files."
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{job_id}/requirements",
    response_model=JobRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    job_id: int,
    data: JobRequirementCreate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> JobRequirement:
    _get_job_or_404(db, user, job_id)
    return job_requirements.create(db, job_id=job_id, data=data)


@router.get("/{job_id}/requirements", response_model=list[JobRequirementResponse])
def list_requirements(
    job_id: int, db: DatabaseSession, user: DevelopmentUser
) -> list[JobRequirement]:
    _get_job_or_404(db, user, job_id)
    return job_requirements.list_for_job(db, job_id=job_id)


@router.patch(
    "/{job_id}/requirements/{requirement_id}",
    response_model=JobRequirementResponse,
)
def update_requirement(
    job_id: int,
    requirement_id: int,
    data: JobRequirementUpdate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> JobRequirement:
    _get_job_or_404(db, user, job_id)
    requirement = _get_requirement_or_404(db, job_id, requirement_id)
    return job_requirements.update(db, requirement=requirement, data=data)


@router.delete(
    "/{job_id}/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_requirement(
    job_id: int,
    requirement_id: int,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Response:
    _get_job_or_404(db, user, job_id)
    requirement = _get_requirement_or_404(db, job_id, requirement_id)
    job_requirements.delete(db, requirement=requirement)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
