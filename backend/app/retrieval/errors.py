from app.errors import AppError


class SearchUnavailableError(AppError):
    status_code = 503
    code = "search_unavailable"


class WorkflowUnavailableError(AppError):
    status_code = 503
    code = "workflow_unavailable"


class EmbeddingFailedError(AppError):
    status_code = 502
    code = "embedding_failed"
