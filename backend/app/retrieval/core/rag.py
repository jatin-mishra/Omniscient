from app.errors import NotImplementedYetError
from app.retrieval.schemas.rag import IngestRequest, IngestResponse, QueryRequest, QueryResponse


async def ingest_document(request: IngestRequest) -> IngestResponse:
    """Chunk, embed and store a document in the vector store."""
    raise NotImplementedYetError("Document ingestion is not implemented yet")


async def answer_query(request: QueryRequest) -> QueryResponse:
    """Retrieve the top_k chunks for the question and generate a grounded answer."""
    raise NotImplementedYetError("Query answering is not implemented yet")
