from app.onboarding.models import Group
from app.onboarding.repositories.base import Repository


class GroupRepository(Repository[Group]):
    model = Group
