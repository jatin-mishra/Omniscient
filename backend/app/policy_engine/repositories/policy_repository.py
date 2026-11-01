from app.db.repository import Repository
from app.policy_engine.models import Policy


class PolicyRepository(Repository[Policy]):
    model = Policy
