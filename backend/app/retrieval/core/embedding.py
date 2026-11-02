"""Text -> vector. Only a constant stub exists for now; real providers plug in behind the
Protocol and the factory, nothing else changes."""

from typing import Protocol

from app.errors import InvalidRequestError


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]:
        """Returns one vector for `text`; its length must equal the configured dimensions."""
        ...


class ConstantEmbeddingProvider:
    """Placeholder: every text maps to the same vector."""

    def __init__(self, dimensions: int, value: float = 0.1) -> None:
        self._vector = [value] * dimensions

    async def embed(self, text: str) -> list[float]:
        return list(self._vector)


def get_embedding_provider(name: str, dimensions: int) -> EmbeddingProvider:
    if name == "constant":
        return ConstantEmbeddingProvider(dimensions)
    raise InvalidRequestError(f"Unknown embedding provider '{name}'")
