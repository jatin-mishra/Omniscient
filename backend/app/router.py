from fastapi import APIRouter

from app import health
from app.onboarding.api.router import router as onboarding_router
from app.retrieval.api.router import router as retrieval_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(onboarding_router)
v1_router.include_router(retrieval_router)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(v1_router)
