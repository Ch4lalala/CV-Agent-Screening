import os
from collections.abc import Generator
from pathlib import Path

os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_development_user
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def resume_storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage_path = tmp_path / "resumes"
    monkeypatch.setenv("CV_STORAGE_PATH", str(storage_path))
    monkeypatch.setenv("MAX_CV_SIZE_MB", "5")
    monkeypatch.setenv("MAX_JOB_DOCUMENT_SIZE_MB", "5")
    return storage_path


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)()

    try:
        yield test_session
    finally:
        test_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def development_user(db_session: Session) -> User:
    user = User(
        email="recruiter@example.com",
        password_hash="not-used-for-authentication",
        full_name="Test Recruiter",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(
    db_session: Session, development_user: User
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_development_user() -> User:
        return development_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_development_user] = override_get_development_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
