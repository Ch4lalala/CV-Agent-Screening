import os
from pathlib import Path


def get_app_environment() -> str:
    return os.getenv("APP_ENV", "development")


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://recruitment_agent:change-me-local-only@localhost:5432/recruitment_agent",
    )


def get_cors_origins() -> list[str]:
    raw_value = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [
        origin.strip().rstrip("/")
        for origin in raw_value.split(",")
        if origin.strip()
    ]


def get_development_user_email() -> str:
    return os.getenv("DEVELOPMENT_USER_EMAIL", "developer@example.com")


def get_development_user_full_name() -> str:
    return os.getenv("DEVELOPMENT_USER_FULL_NAME", "Development Recruiter")


def get_cv_storage_path() -> Path:
    return Path(os.getenv("CV_STORAGE_PATH", "storage/resumes")).expanduser().resolve()


def get_max_cv_size_bytes() -> int:
    raw_value = os.getenv("MAX_CV_SIZE_MB", "5")
    try:
        size_mb = float(raw_value)
    except ValueError as exc:
        raise RuntimeError("MAX_CV_SIZE_MB must be a positive number") from exc
    if size_mb <= 0:
        raise RuntimeError("MAX_CV_SIZE_MB must be a positive number")
    return int(size_mb * 1024 * 1024)
