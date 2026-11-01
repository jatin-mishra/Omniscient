from fastapi import APIRouter

from app.retrieval.api import chunks, directories, documents

router = APIRouter()
router.include_router(directories.router)
router.include_router(documents.router)
router.include_router(chunks.router)
