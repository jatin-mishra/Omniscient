from fastapi import APIRouter

from app import health
from app.onboarding.api.router import router as onboarding_router
from app.policy_engine.api.router import router as policy_engine_router
from app.retrieval.api.router import router as retrieval_router
from app.tracker.api.router import router as tracker_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(onboarding_router)
v1_router.include_router(policy_engine_router)
v1_router.include_router(retrieval_router)
v1_router.include_router(tracker_router)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(v1_router)
