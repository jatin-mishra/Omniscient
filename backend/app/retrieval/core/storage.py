"""Raw-file storage per cloud provider. Both implementations are empty on purpose: uploading
bytes is out of scope for now and nothing in the API calls them yet."""

from dataclasses import dataclass
from typing import Protocol

from app.errors import NotImplementedYetError
from app.retrieval.models import Provider


@dataclass(frozen=True)
class StoredObject:
    etag: str
    url: str


class StorageProvider(Protocol):
    provider: Provider

    async def upload(
        self, bucket: str, path: str, content: bytes, content_type: str
    ) -> StoredObject:
        """Stores `content` at bucket/path and returns its etag and URL."""
        ...


class S3StorageProvider:
    provider = Provider.AWS

    async def upload(
        self, bucket: str, path: str, content: bytes, content_type: str
    ) -> StoredObject:
        raise NotImplementedYetError("S3 upload is not implemented yet")


class GcpStorageProvider:
    provider = Provider.GCP

    async def upload(
        self, bucket: str, path: str, content: bytes, content_type: str
    ) -> StoredObject:
        raise NotImplementedYetError("GCP upload is not implemented yet")


def get_storage_provider(provider: Provider) -> StorageProvider:
    return S3StorageProvider() if provider is Provider.AWS else GcpStorageProvider()
