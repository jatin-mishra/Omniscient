from collections.abc import Iterable

from app.errors import NotFoundError
from app.tracker.core.providers.base import TicketProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[TicketProvider]) -> None:
        self._by_name = {p.name.value: p for p in providers}

    def get(self, name: str) -> TicketProvider:
        provider = self._by_name.get(name)
        if provider is None:
            raise NotFoundError(f"Unknown ticket provider '{name}'")
        return provider
