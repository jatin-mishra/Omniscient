from app.db.repository import Repository
from app.retrieval.models import Document


class DocumentRepository(Repository[Document]):
    model = Document
