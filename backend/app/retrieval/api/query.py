from fastapi import APIRouter

from app.retrieval.core import rag
from app.retrieval.schemas.rag import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


@router.post("")
async def answer_query(request: QueryRequest) -> QueryResponse:
    return await rag.answer_query(request)
