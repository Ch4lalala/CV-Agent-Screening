from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resume_document import ResumeDocument


def get_for_candidate(db: Session, *, candidate_id: int) -> ResumeDocument | None:
    return db.scalar(
        select(ResumeDocument).where(ResumeDocument.candidate_id == candidate_id)
    )

