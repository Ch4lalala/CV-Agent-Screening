import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.config import get_cors_origins
from app.services.development_user import seed_development_user


def _configure_application_logging() -> None:
    application_logger = logging.getLogger("app")
    server_logger = logging.getLogger("uvicorn.error")
    if server_logger.handlers:
        application_logger.handlers = server_logger.handlers
        application_logger.propagate = False
    application_logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _configure_application_logging()
    seed_development_user()
    yield


app = FastAPI(
    title="Evidence-Grounded Recruitment Agent API",
    version="0.8.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)

app.include_router(api_router)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "A database operation failed"},
    )


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report whether the API process is available."""
    return {"status": "healthy"}
