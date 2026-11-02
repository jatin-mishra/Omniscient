from app.db.repository import Repository
from app.retrieval.models import Directory


class DirectoryRepository(Repository[Directory]):
    model = Directory
