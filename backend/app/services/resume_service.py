import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import fitz
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.config import get_cv_storage_path, get_max_cv_size_bytes
from app.models.candidate import Candidate
from app.models.enums import CandidateStatus, ResumeExtractionStatus
from app.models.job import Job
from app.models.resume_document import ResumeDocument

_CHUNK_SIZE = 64 * 1024
_PDF_SIGNATURE = b"%PDF-"
_ALLOWED_MIME_TYPE = "application/pdf"
_EMPTY_TEXT_MESSAGE = (
    "Unable to extract meaningful text from this PDF. "
    "Please upload a text-based resume."
)


class ResumeIngestionError(Exception):
    pass


class UnsupportedResumeFormatError(ResumeIngestionError):
    pass


class ResumeTooLargeError(ResumeIngestionError):
    pass


class InvalidPdfError(ResumeIngestionError):
    pass


class ResumeStorageError(ResumeIngestionError):
    pass


@dataclass(frozen=True)
class StoredResume:
    original_filename: str
    stored_filename: str
    path: Path


@dataclass(frozen=True)
class ExtractedPage:
    page: int
    text: str


@dataclass(frozen=True)
class ResumeExtraction:
    page_count: int
    text: str
    pages: list[ExtractedPage]
    status: ResumeExtractionStatus
    error_message: str | None = None


@dataclass(frozen=True)
class StagedDeletion:
    original_path: Path
    staged_path: Path


def normalize_resume_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\x00", "")
    normalized = "\n".join(line.rstrip(" \t") for line in normalized.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


def _sanitize_original_filename(filename: str | None) -> str:
    if not filename:
        raise UnsupportedResumeFormatError("A PDF filename is required")

    basename = Path(filename.replace("\\", "/")).name.replace("\x00", "").strip()
    if not basename or Path(basename).suffix.lower() != ".pdf":
        raise UnsupportedResumeFormatError("Unsupported file format. Upload a PDF file.")

    if len(basename) > 255:
        basename = f"{Path(basename).stem[:251]}.pdf"
    return basename


def _validate_mime_type(content_type: str | None) -> None:
    if (content_type or "").lower() != _ALLOWED_MIME_TYPE:
        raise UnsupportedResumeFormatError(
            "Unsupported file format. The file MIME type must be application/pdf."
        )


async def store_resume_upload(upload: UploadFile) -> StoredResume:
    original_filename = _sanitize_original_filename(upload.filename)
    _validate_mime_type(upload.content_type)

    storage_root = get_cv_storage_path()
    stored_filename = f"{uuid4()}.pdf"
    final_path = storage_root / stored_filename
    temporary_path = storage_root / f".{stored_filename}.uploading"
    maximum_size = get_max_cv_size_bytes()
    bytes_written = 0
    first_chunk = True

    try:
        storage_root.mkdir(parents=True, exist_ok=True)
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(_CHUNK_SIZE):
                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(_PDF_SIGNATURE):
                        raise InvalidPdfError(
                            "Invalid PDF file. The PDF signature is missing."
                        )

                bytes_written += len(chunk)
                if bytes_written > maximum_size:
                    raise ResumeTooLargeError("Resume file exceeds allowed size.")
                destination.write(chunk)

        if bytes_written == 0:
            raise InvalidPdfError("Invalid PDF file. The PDF signature is missing.")

        os.replace(temporary_path, final_path)
    except ResumeIngestionError:
        temporary_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise ResumeStorageError("Unable to store the resume file.") from exc

    return StoredResume(
        original_filename=original_filename,
        stored_filename=stored_filename,
        path=final_path,
    )


def extract_pdf_text(path: Path) -> ResumeExtraction:
    try:
        document = fitz.open(path)
    except (fitz.FileDataError, fitz.EmptyFileError, RuntimeError) as exc:
        raise InvalidPdfError("Invalid or unreadable PDF file.") from exc

    with document:
        if document.needs_pass:
            raise InvalidPdfError("Encrypted PDF files are not supported.")

        page_count = document.page_count
        pages: list[ExtractedPage] = []
        try:
            for page_index in range(page_count):
                page_text = normalize_resume_text(
                    document.load_page(page_index).get_text("text")
                )
                pages.append(ExtractedPage(page=page_index + 1, text=page_text))
        except (RuntimeError, ValueError):
            return ResumeExtraction(
                page_count=page_count,
                text="",
                pages=pages,
                status=ResumeExtractionStatus.FAILED,
                error_message="Unable to extract text from this PDF.",
            )

    combined_text = normalize_resume_text(
        "\n\n".join(page.text for page in pages if page.text)
    )
    if not combined_text:
        return ResumeExtraction(
            page_count=page_count,
            text="",
            pages=pages,
            status=ResumeExtractionStatus.FAILED,
            error_message=_EMPTY_TEXT_MESSAGE,
        )

    return ResumeExtraction(
        page_count=page_count,
        text=combined_text,
        pages=pages,
        status=ResumeExtractionStatus.COMPLETED,
    )


def _safe_stored_path(stored_filename: str | None) -> Path | None:
    if not stored_filename:
        return None

    storage_root = get_cv_storage_path()
    candidate_path = (storage_root / stored_filename).resolve()
    if candidate_path.parent != storage_root or candidate_path.suffix.lower() != ".pdf":
        return None
    return candidate_path


def remove_stored_resume(stored_filename: str) -> None:
    stored_path = _safe_stored_path(stored_filename)
    if stored_path is None:
        return
    try:
        stored_path.unlink(missing_ok=True)
    except OSError as exc:
        raise ResumeStorageError("Unable to remove the stored resume file.") from exc


def _stage_resume_deletion(stored_filename: str | None) -> StagedDeletion | None:
    stored_path = _safe_stored_path(stored_filename)
    if stored_path is None or not stored_path.exists():
        return None

    staged_path = stored_path.with_name(f".{stored_path.name}.{uuid4()}.deleting")
    try:
        stored_path.replace(staged_path)
    except OSError as exc:
        raise ResumeStorageError("Unable to remove the stored resume file.") from exc
    return StagedDeletion(original_path=stored_path, staged_path=staged_path)


def _restore_staged_deletions(staged_deletions: list[StagedDeletion]) -> None:
    for staged in staged_deletions:
        if staged.staged_path.exists():
            staged.staged_path.replace(staged.original_path)


def _finalize_staged_deletions(staged_deletions: list[StagedDeletion]) -> None:
    for staged in staged_deletions:
        try:
            staged.staged_path.unlink(missing_ok=True)
        except OSError:
            # Database deletion has completed. Any leftover staged file remains
            # confined to the private resume directory for manual cleanup.
            pass


async def ingest_candidate_resume(
    db: Session,
    *,
    job_id: int,
    upload: UploadFile,
    name: str | None,
    email: str | None,
) -> tuple[Candidate, ResumeDocument]:
    stored = await store_resume_upload(upload)
    try:
        extraction = await run_in_threadpool(extract_pdf_text, stored.path)
    except InvalidPdfError:
        remove_stored_resume(stored.stored_filename)
        raise

    candidate = Candidate(
        job_id=job_id,
        name=name,
        email=email,
        original_filename=stored.original_filename,
        resume_path=stored.stored_filename,
        status=CandidateStatus.UPLOADED,
    )
    resume_document = ResumeDocument(
        candidate=candidate,
        extracted_text=extraction.text,
        page_count=extraction.page_count,
        extraction_status=extraction.status,
        extraction_error=extraction.error_message,
    )
    db.add(candidate)
    db.add(resume_document)

    try:
        db.commit()
        db.refresh(candidate)
        db.refresh(resume_document)
    except SQLAlchemyError:
        db.rollback()
        remove_stored_resume(stored.stored_filename)
        raise

    return candidate, resume_document


def delete_candidate_and_resume(db: Session, *, candidate: Candidate) -> None:
    staged = _stage_resume_deletion(candidate.resume_path)
    staged_deletions = [staged] if staged is not None else []
    try:
        db.delete(candidate)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        _restore_staged_deletions(staged_deletions)
        raise

    _finalize_staged_deletions(staged_deletions)


def delete_job_and_resumes(db: Session, *, job: Job) -> None:
    staged_deletions: list[StagedDeletion] = []
    try:
        for candidate in job.candidates:
            staged = _stage_resume_deletion(candidate.resume_path)
            if staged is not None:
                staged_deletions.append(staged)
    except ResumeStorageError:
        _restore_staged_deletions(staged_deletions)
        raise

    try:
        db.delete(job)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        _restore_staged_deletions(staged_deletions)
        raise

    _finalize_staged_deletions(staged_deletions)
