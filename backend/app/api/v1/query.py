from fastapi import APIRouter

from app.schemas.rag import QueryRequest, QueryResponse
from app.services import rag

router = APIRouter(prefix="/query", tags=["query"])


@router.post("")
async def answer_query(request: QueryRequest) -> QueryResponse:
    return await rag.answer_query(request)
