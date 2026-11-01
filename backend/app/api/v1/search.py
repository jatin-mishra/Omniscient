from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_chunk_search_repo
from app.repositories.chunk_search_repository import ChunkSearchRepository
from app.schemas.rag import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
async def search(
    request: SearchRequest,
    repo: Annotated[ChunkSearchRepository, Depends(get_chunk_search_repo)],
) -> SearchResponse:
    return SearchResponse(hits=await repo.search(request.query, request.top_k))
