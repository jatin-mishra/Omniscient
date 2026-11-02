from enum import StrEnum


class Provider(StrEnum):
    AWS = "aws"
    GCP = "gcp"


class UploadStatus(StrEnum):
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ChunkState(StrEnum):
    CHUNKING = "chunking"
    MEDIA_CAPTIONING = "media_captioning"
    CONTEXTUALIZING = "contextualizing"
    WORK_ITEM_CREATION = "work_item_creation"
    EMBEDDING = "embedding"


class StateStatus(StrEnum):
    IN_PROGRESS = "in-progress"
    SUCCESS = "success"
    FAILURE = "failure"
