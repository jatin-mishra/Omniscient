from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.deps import get_db_session
from app.entity_verifier import SqlEntityVerifier
from app.tracker.core.providers import InternalProvider, ProviderRegistry
from app.tracker.core.ticket_service import TicketService
from app.tracker.repositories.ticket_repository import TicketRepository

Session = Annotated[AsyncSession, Depends(get_db_session)]


def get_ticket_service(session: Session) -> TicketService:
    providers = ProviderRegistry([InternalProvider(get_settings().tracker_webhook_secret)])
    return TicketService(session, TicketRepository(session), providers, SqlEntityVerifier(session))
