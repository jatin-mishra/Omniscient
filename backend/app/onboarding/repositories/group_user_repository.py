from app.onboarding.models import GroupUser
from app.onboarding.repositories.base import Repository


class GroupUserRepository(Repository[GroupUser]):
    model = GroupUser
