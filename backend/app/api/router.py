from fastapi import APIRouter

from app.api import candidates, jobs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(jobs.router)
api_router.include_router(candidates.router)

