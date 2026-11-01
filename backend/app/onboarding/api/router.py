from fastapi import APIRouter

from app.onboarding.api import group_users, groups, teams, users

router = APIRouter()
router.include_router(teams.router)
router.include_router(users.router)
router.include_router(groups.router)
router.include_router(group_users.router)
