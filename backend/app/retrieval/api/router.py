from fastapi import APIRouter

from app.retrieval.api import chunk_vectors, chunks, directories, documents, workflows

router = APIRouter()
router.include_router(directories.router)
router.include_router(documents.router)
router.include_router(chunks.router)
router.include_router(chunk_vectors.router)
router.include_router(workflows.router)
