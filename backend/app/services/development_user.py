from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import (
    get_app_environment,
    get_development_user_email,
    get_development_user_full_name,
)
from app.database.session import SessionLocal, get_db
from app.models.user import User
from app.repositories import users

_NON_AUTHENTICATING_PASSWORD_MARKER = "authentication-not-implemented"


def seed_development_user() -> None:
    """Create the one temporary recruiter used before authentication exists."""
    if get_app_environment() != "development":
        return

    with SessionLocal() as db:
        email = get_development_user_email()
        if users.get_by_email(db, email) is None:
            users.create(
                db,
                email=email,
                full_name=get_development_user_full_name(),
                password_hash=_NON_AUTHENTICATING_PASSWORD_MARKER,
            )


def get_development_user(db: Annotated[Session, Depends(get_db)]) -> User:
    """Resolve the temporary recruiter in one replaceable dependency."""
    if get_app_environment() != "development":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )

    user = users.get_by_email(db, get_development_user_email())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Development user is not initialized",
        )
    return user
