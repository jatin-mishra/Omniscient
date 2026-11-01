from fastapi import APIRouter

from app.api.v1 import documents, query

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(documents.router)
v1_router.include_router(query.router)
