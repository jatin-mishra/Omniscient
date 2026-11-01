from fastapi import APIRouter

from app.retrieval.api import documents, query, search

router = APIRouter()
router.include_router(documents.router)
router.include_router(query.router)
router.include_router(search.router)
