from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.api.dependencies import DatabaseSession, DevelopmentUser
from app.models.candidate import Candidate
from app.repositories import candidates, jobs, resume_documents
from app.schemas.candidate import (
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
    CandidateUploadMetadata,
    CandidateUploadResponse,
)
from app.schemas.resume import ResumeMetadataResponse, ResumeSummaryResponse
from app.services import resume_service

router = APIRouter(tags=["candidates"])


def _get_job_or_404(db: DatabaseSession, user: DevelopmentUser, job_id: int) -> None:
    if jobs.get_for_user(db, job_id=job_id, user_id=user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


def _get_candidate_or_404(
    db: DatabaseSession, user: DevelopmentUser, candidate_id: int
) -> Candidate:
    candidate = candidates.get_for_user(db, candidate_id=candidate_id, user_id=user.id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate


@router.post(
    "/jobs/{job_id}/candidates",
    response_model=CandidateUploadResponse | CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "name": {"type": "string", "nullable": True},
                            "email": {
                                "type": "string",
                                "format": "email",
                                "nullable": True,
                            },
                        },
                    }
                }
            },
        }
    },
)
async def create_candidate(
    job_id: int,
    request: Request,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Candidate | CandidateUploadResponse:
    _get_job_or_404(db, user, job_id)
    content_type = request.headers.get("content-type", "").lower()

    if content_type.startswith("application/json"):
        try:
            data = CandidateCreate.model_validate(await request.json())
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON request body",
            ) from exc
        return candidates.create(db, job_id=job_id, data=data)

    if not content_type.startswith("multipart/form-data"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported request format. Upload a PDF using multipart/form-data.",
        )

    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A PDF file is required",
        )

    def optional_string(value: Any) -> str | None:
        return value if isinstance(value, str) and value.strip() else None

    try:
        metadata = CandidateUploadMetadata.model_validate(
            {
                "name": optional_string(form.get("name")),
                "email": optional_string(form.get("email")),
            }
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    try:
        candidate, resume_document = await resume_service.ingest_candidate_resume(
            db,
            job_id=job_id,
            upload=upload,
            name=metadata.name,
            email=str(metadata.email) if metadata.email is not None else None,
        )
    except resume_service.UnsupportedResumeFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except resume_service.InvalidPdfError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except resume_service.ResumeTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except resume_service.ResumeStorageError as exc:
        raise HTTPException(
            status_code=500, detail="Unable to process the resume file."
        ) from exc
    finally:
        await upload.close()

    return CandidateUploadResponse(
        **CandidateResponse.model_validate(candidate).model_dump(),
        resume=ResumeSummaryResponse(
            page_count=resume_document.page_count,
            extraction_status=resume_document.extraction_status,
            text_length=len(resume_document.extracted_text or ""),
            message=resume_document.extraction_error,
        ),
    )


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateResponse])
def list_candidates(
    job_id: int, db: DatabaseSession, user: DevelopmentUser
) -> list[Candidate]:
    _get_job_or_404(db, user, job_id)
    return candidates.list_for_job(db, job_id=job_id)


@router.get("/candidates/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int, db: DatabaseSession, user: DevelopmentUser
) -> Candidate:
    return _get_candidate_or_404(db, user, candidate_id)


@router.get(
    "/candidates/{candidate_id}/resume",
    response_model=ResumeMetadataResponse,
)
def get_candidate_resume(
    candidate_id: int, db: DatabaseSession, user: DevelopmentUser
) -> ResumeMetadataResponse:
    candidate = _get_candidate_or_404(db, user, candidate_id)
    resume_document = resume_documents.get_for_candidate(db, candidate_id=candidate.id)
    if resume_document is None or candidate.original_filename is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    return ResumeMetadataResponse(
        original_filename=candidate.original_filename,
        page_count=resume_document.page_count,
        extraction_status=resume_document.extraction_status,
        text_length=len(resume_document.extracted_text or ""),
        message=resume_document.extraction_error,
    )


@router.patch("/candidates/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    db: DatabaseSession,
    user: DevelopmentUser,
) -> Candidate:
    candidate = _get_candidate_or_404(db, user, candidate_id)
    return candidates.update(db, candidate=candidate, data=data)


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int, db: DatabaseSession, user: DevelopmentUser
) -> Response:
    candidate = _get_candidate_or_404(db, user, candidate_id)
    try:
        resume_service.delete_candidate_and_resume(db, candidate=candidate)
    except resume_service.ResumeStorageError as exc:
        raise HTTPException(
            status_code=500, detail="Unable to remove the stored resume file."
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
