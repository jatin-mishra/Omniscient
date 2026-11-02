from fastapi import APIRouter

from app.policy_engine.api import policies, user_permissions

router = APIRouter()
router.include_router(policies.router)
router.include_router(user_permissions.router)
