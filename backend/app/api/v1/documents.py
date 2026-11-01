from fastapi import APIRouter, status

from app.schemas.rag import IngestRequest, IngestResponse
from app.services import rag

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def ingest_document(request: IngestRequest) -> IngestResponse:
    return await rag.ingest_document(request)
