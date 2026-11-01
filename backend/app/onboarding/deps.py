from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db_session
from app.onboarding.core.group_service import GroupService
from app.onboarding.core.group_user_service import GroupUserService
from app.onboarding.core.team_service import TeamService
from app.onboarding.core.user_service import UserService
from app.onboarding.repositories.group_repository import GroupRepository
from app.onboarding.repositories.group_user_repository import GroupUserRepository
from app.onboarding.repositories.team_repository import TeamRepository
from app.onboarding.repositories.user_repository import UserRepository

Session = Annotated[AsyncSession, Depends(get_db_session)]


def get_team_service(session: Session) -> TeamService:
    return TeamService(session, TeamRepository(session), UserRepository(session))


def get_user_service(session: Session) -> UserService:
    return UserService(session, UserRepository(session), TeamRepository(session))


def get_group_service(session: Session) -> GroupService:
    return GroupService(session, GroupRepository(session))


def get_group_user_service(session: Session) -> GroupUserService:
    return GroupUserService(
        session, GroupUserRepository(session), GroupRepository(session), UserRepository(session)
    )
