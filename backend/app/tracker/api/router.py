from fastapi import APIRouter

from app.tracker.api import tickets

router = APIRouter()
router.include_router(tickets.router)
