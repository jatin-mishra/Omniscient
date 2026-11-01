from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document


class DocumentRepository:
    """Data access for the `documents` table. Does not commit; the caller owns the transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, source: str, text: str) -> Document:
        document = Document(source=source, text=text)
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def get(self, document_id: UUID) -> Document | None:
        return await self._session.get(Document, document_id)
