from app.db.repository import Repository
from app.retrieval.models import ChunkVector


class ChunkVectorRepository(Repository[ChunkVector]):
    model = ChunkVector
