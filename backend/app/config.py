import os


def get_app_environment() -> str:
    return os.getenv("APP_ENV", "development")


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://recruitment_agent:change-me-local-only@localhost:5432/recruitment_agent",
    )


def get_development_user_email() -> str:
    return os.getenv("DEVELOPMENT_USER_EMAIL", "developer@example.com")


def get_development_user_full_name() -> str:
    return os.getenv("DEVELOPMENT_USER_FULL_NAME", "Development Recruiter")
